"""
conversation.py — Datazo by Coinplay

THREE LAYERS:
  LAYER 1 — MENU (always wins): menu button → feature handler
  LAYER 2 — ONBOARDING (free text, first 2 exchanges): regions → bet style/tracks → bridge
  LAYER 3 — ASSISTANT (free text, post-onboarding): Valentina answers, FTD detection active
"""
import asyncio, logging, time
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from config import State, COINPLAY_REG_URL
from storage import get_user, update_user, get_preferences, append_history, log_barrier
from ai_agent import get_ai_response, detect_ftd
from onboarding import process_onboarding_answer, DONE_MSG, format_preferences_summary
from messages import (
    BRIDGE, CTA_REGISTER, FTD_CELEBRATION,
    BARRIER_FALLBACK, GENERIC_FALLBACK,
    MORNING_DIGEST_HEADER, MORNING_DIGEST_FOOTER,
)
from ftd_onboarding import start_repeat_machine
from racing import (
    fetch_race_context,
    format_live_races_message, format_racecard_message,
)
from predictions import generate_daily_predictions, format_predictions_message, get_stats_display
from media import send_pic, sanitize_markdown

logger = logging.getLogger(__name__)


def _T(lang, en, ru, es):
    return {"en": en, "ru": ru, "es": es}.get(lang, en)


# ── Persistent menu ───────────────────────────────────────────────────────────

def main_menu(lang: str) -> ReplyKeyboardMarkup:
    if lang == "es":
        buttons = [
            ["🔴 En Vivo",          "🏇 Programa de Hoy"],
            ["🎯 Picks de Valentina", "📊 Historial"],
            ["💰 Cómo Gano"],
        ]
    elif lang == "ru":
        buttons = [
            ["🔴 Прямой эфир",   "🏇 Программа дня"],
            ["🎯 Пики Валентины", "📊 Статистика"],
            ["💰 Как я зарабатываю"],
        ]
    else:
        buttons = [
            ["🔴 Live Races",      "🏇 Today's Card"],
            ["🎯 Valentina's Tips", "📊 Track Record"],
            ["💰 How I Profit"],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


MENU_ACTIONS = {
    # EN
    "🔴 Live Races": "live", "🏇 Today's Card": "today",
    "🎯 Valentina's Tips": "picks", "📊 Track Record": "stats", "💰 How I Profit": "bridge",
    # RU
    "🔴 Прямой эфир": "live", "🏇 Программа дня": "today",
    "🎯 Пики Валентины": "picks", "📊 Статистика": "stats", "💰 Как я зарабатываю": "bridge",
    # ES
    "🔴 En Vivo": "live", "🏇 Programa de Hoy": "today",
    "🎯 Picks de Valentina": "picks", "📊 Historial": "stats", "💰 Cómo Gano": "bridge",
}


# ── Send helpers ──────────────────────────────────────────────────────────────

def _delay(text: str) -> float:
    return round(1.0 + min(len(text) / 160, 2.0), 1)

def _reg_label(lang):
    return _T(lang, "🎯 Register on Coinplay", "🎯 Регистрация в Coinplay", "🎯 Registrarme en Coinplay")

async def _send(bot: Bot, chat_id: int, text: str, lang: str, inline=None):
    await bot.send_chat_action(chat_id, "typing")
    await asyncio.sleep(_delay(text))
    await bot.send_message(
        chat_id=chat_id, text=sanitize_markdown(text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=inline or main_menu(lang),
        disable_web_page_preview=True,
    )

async def _send_with_reg(bot: Bot, chat_id: int, text: str, lang: str):
    inline = InlineKeyboardMarkup([[InlineKeyboardButton(_reg_label(lang), url=COINPLAY_REG_URL)]])
    await bot.send_chat_action(chat_id, "typing")
    await asyncio.sleep(_delay(text))
    await bot.send_message(
        chat_id=chat_id, text=sanitize_markdown(text),
        parse_mode=ParseMode.MARKDOWN, reply_markup=inline,
        disable_web_page_preview=True,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

async def handle_message(bot: Bot, user_id: int, chat_id: int, text: str, lang: str):
    action = MENU_ACTIONS.get(text)
    if action:
        await handle_menu_action(bot, user_id, chat_id, lang, action)
        return

    u               = get_user(user_id, lang)
    state           = u.get("state", State.NEW)
    history         = u.get("history", [])
    barriers        = u.get("barriers", [])
    onboarding_done = u.get("onboarding_done", False)
    onboarding_step = u.get("onboarding_turn", 0)
    prefs           = u.get("preferences", {})

    update_user(user_id, message_count=u.get("message_count", 0) + 1)
    append_history(user_id, "user", text)

    if state in (State.CONVERTING, State.BRIDGE, State.WARMUP, State.DEPOSITED):
        if await detect_ftd(text, lang):
            await _handle_ftd(bot, user_id, chat_id, lang)
            return

    if not onboarding_done:
        await _run_onboarding(bot, user_id, chat_id, text, lang, onboarding_step)
        return

    ctx = await fetch_race_context()
    ai  = await get_ai_response(
        user_message=text, lang=lang, state=state, history=history, barriers=barriers,
        real_live=ctx["live"], real_upcoming=ctx["upcoming"], prefs=prefs,
    )

    if ai["barrier"]:
        log_barrier(user_id, ai["barrier"])
        bf = BARRIER_FALLBACK.get(ai["barrier"], {})
        barrier_text = bf.get(lang) or bf.get("en")
        if barrier_text:
            append_history(user_id, "assistant", barrier_text)
            await _send(bot, chat_id, barrier_text, lang)
            return

    if ai["next"] == "converting" and state not in (State.CONVERTING, State.DEPOSITED, State.REPEAT):
        update_user(user_id, state=State.CONVERTING)
        await _send_cta(bot, user_id, chat_id, lang)
        return
    elif ai["next"] == "bridge" and state == State.WARMUP:
        await _send_bridge(bot, user_id, chat_id, lang)
        return

    if ai["intent"] == "deposit_ready" and state != State.DEPOSITED:
        update_user(user_id, state=State.CONVERTING)
        await _send_cta(bot, user_id, chat_id, lang)
        return

    reply = ai["text"] or GENERIC_FALLBACK.get(lang, GENERIC_FALLBACK["en"])
    append_history(user_id, "assistant", reply)
    await _send(bot, chat_id, reply, lang)


# ── Layer 2: Onboarding ───────────────────────────────────────────────────────

async def _run_onboarding(bot, user_id, chat_id, text, lang, step):
    next_question, complete = await process_onboarding_answer(user_id, text, step, lang)
    update_user(user_id, onboarding_turn=step + 1)

    if not complete:
        append_history(user_id, "assistant", next_question)
        pic_moment = "onboarding1" if step == 0 else "onboarding2"
        sent = await send_pic(bot, chat_id, pic_moment, next_question, lang)
        if not sent:
            await _send(bot, chat_id, next_question, lang)
    else:
        update_user(user_id, onboarding_done=True, state=State.BRIDGE)
        prefs   = get_preferences(user_id)
        summary = format_preferences_summary(prefs, lang)
        if summary:
            await _send(bot, chat_id, summary, lang)
            await asyncio.sleep(1.0)
        await _send_bridge(bot, user_id, chat_id, lang, DONE_MSG.get(lang, DONE_MSG["en"]))


# ── Menu action handler ───────────────────────────────────────────────────────

async def handle_menu_action(bot: Bot, user_id: int, chat_id: int, lang: str, action: str):
    u     = get_user(user_id)
    state = u.get("state", State.NEW)
    prefs = u.get("preferences", {})

    if action == "bridge":
        update_user(user_id, onboarding_done=True)
        if u.get("bridge_shown") and state not in (State.DEPOSITED, State.REPEAT):
            update_user(user_id, state=State.CONVERTING)
            await _send_cta(bot, user_id, chat_id, lang)
        else:
            update_user(user_id, state=State.BRIDGE)
            await _send_bridge(bot, user_id, chat_id, lang)
        return

    if action == "stats":
        text = get_stats_display(lang)
        if state not in (State.DEPOSITED, State.REPEAT):
            await _send_with_reg(bot, chat_id, text, lang)
        else:
            await _send(bot, chat_id, text, lang)
        return

    try:
        ctx = await fetch_race_context()
    except Exception as e:
        logger.error(f"fetch_race_context failed: {e}", exc_info=True)
        err = _T(lang, "📡 Couldn't load racing data — try again in a moment.",
                       "📡 Не удалось загрузить данные — попробуй ещё раз.",
                       "📡 No se pudo cargar la data — probá de nuevo.")
        await _send(bot, chat_id, err, lang)
        return

    if action == "live":
        display = ctx["for_display"]
        is_mock = not ctx.get("has_real_live", ctx["has_real"])
        text    = format_live_races_message(display["live"], lang, is_mock=is_mock)
        if state not in (State.DEPOSITED, State.REPEAT) and not is_mock:
            text += _T(lang,
                "\n\n💡 _Want to act on these? That's what Coinplay is for._",
                "\n\n💡 _Хочешь сыграть на это? Для этого и есть Coinplay._",
                "\n\n💡 _¿Querés jugarlas? Para eso uso Coinplay._")
        await _send(bot, chat_id, text, lang)

    elif action == "today":
        display = ctx["for_display"]
        is_mock = not ctx.get("has_real_upcoming", ctx["has_real"])
        header  = MORNING_DIGEST_HEADER.get(lang, MORNING_DIGEST_HEADER["en"])
        body    = format_racecard_message(display["upcoming"], lang, is_mock=is_mock)
        footer  = MORNING_DIGEST_FOOTER.get(lang, MORNING_DIGEST_FOOTER["en"])
        await _send(bot, chat_id, header + body + footer, lang)

    elif action == "picks":
        races = ctx["live"] + ctx["upcoming"] if ctx["has_real"] else []
        races = _filter_races_by_prefs(races, prefs)
        tips  = await generate_daily_predictions(races, lang)
        text  = format_predictions_message(tips, lang)

        note = _personalization_note(prefs, lang)
        if note:
            text = note + "\n\n" + text

        if state not in (State.DEPOSITED, State.REPEAT):
            inline = InlineKeyboardMarkup([[InlineKeyboardButton(_reg_label(lang), url=COINPLAY_REG_URL)]])
            sent = await send_pic(bot, chat_id, "picks", text, lang, reply_markup=inline)
            if not sent:
                await _send_with_reg(bot, chat_id, text, lang)
        else:
            sent = await send_pic(bot, chat_id, "picks", text, lang)
            if not sent:
                await _send(bot, chat_id, text, lang)


def _filter_races_by_prefs(races: list, prefs: dict) -> list:
    """Soft filter by favourite tracks if any are set (keeps all if no match)."""
    tracks = [t.lower() for t in prefs.get("tracks", [])]
    if not tracks:
        return races
    matched = [r for r in races if any(t in (r.get("course", "").lower()) for t in tracks)]
    return matched or races


def _personalization_note(prefs: dict, lang: str) -> str:
    items = []
    if prefs.get("tracks"):
        items.extend(prefs["tracks"][:2])
    elif prefs.get("regions"):
        items.extend(prefs["regions"][:2])
    if not items:
        return ""
    focused = ", ".join(items)
    return _T(lang,
        f"🎯 _Filtered for your profile: {focused}_",
        f"🎯 _Под твой профиль: {focused}_",
        f"🎯 _Filtrado para tu perfil: {focused}_")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_bridge(bot, user_id, chat_id, lang, intro_text: str = None):
    update_user(user_id, state=State.BRIDGE, bridge_shown=True)
    inline = InlineKeyboardMarkup([[InlineKeyboardButton(_reg_label(lang), url=COINPLAY_REG_URL)]])
    if intro_text:
        append_history(user_id, "assistant", intro_text)
        await _send(bot, chat_id, intro_text, lang)
        await asyncio.sleep(1.5)
    bridge_text = BRIDGE.get(lang, BRIDGE["en"])
    append_history(user_id, "assistant", bridge_text)
    await send_pic(bot, chat_id, "bridge", bridge_text, lang, reply_markup=inline)


async def _send_cta(bot, user_id, chat_id, lang):
    update_user(user_id, state=State.CONVERTING, reg_link_sent=True)
    text   = CTA_REGISTER.get(lang, CTA_REGISTER["en"]).format(url=COINPLAY_REG_URL)
    inline = InlineKeyboardMarkup([[InlineKeyboardButton(_reg_label(lang), url=COINPLAY_REG_URL)]])
    append_history(user_id, "assistant", text)
    await send_pic(bot, chat_id, "cta", text, lang, reply_markup=inline)


async def _handle_ftd(bot, user_id, chat_id, lang):
    update_user(user_id, state=State.DEPOSITED, ftd_at=time.time())
    text = FTD_CELEBRATION.get(lang, FTD_CELEBRATION["en"])
    append_history(user_id, "assistant", text)
    await send_pic(bot, chat_id, "ftd", text, lang)
    await start_repeat_machine(bot, user_id, chat_id, lang)
