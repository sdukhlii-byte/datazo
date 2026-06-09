"""
bot.py — Datazo by Coinplay
Commands: /start /live /today /picks /stats /signal /record /apitest /policy
"""
import asyncio, logging, os, sys, atexit
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode
from config import BOT_TOKEN, BOT_USERNAME, HOOK_IMAGE, State, TG_LANG_MAP, DEFAULT_LANG
from storage import get_user, update_user, append_history
from conversation import handle_message, handle_menu_action, main_menu
from signals import run_signal_scheduler
from ftd_onboarding import resume_pending_repeats
from messages import HOOK_CAPTION
from media import send_pic

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

LOCK_FILE = "/tmp/datazo_bot.lock"

def _check_lock():
    if os.path.exists(LOCK_FILE):
        try:
            pid = int(open(LOCK_FILE).read().strip())
            os.kill(pid, 0)
            logger.critical(f"Already running (PID {pid}). Exiting.")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            os.remove(LOCK_FILE)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))

_check_lock()

def _detect_lang(code):
    if not code:
        return DEFAULT_LANG
    return TG_LANG_MAP.get(code.split("-")[0].lower(), DEFAULT_LANG)

def _admin_ids():
    raw = os.environ.get("ADMIN_IDS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    lang    = _detect_lang(user.language_code)   # auto: en / ru / es
    u_check = get_user(user.id, lang)
    is_new  = u_check.get("message_count", 0) == 0
    if is_new:
        update_user(user.id, lang=lang, state=State.NEW,
                    onboarding_done=False, onboarding_turn=0, stage_replies=0)
    else:
        update_user(user.id, lang=lang)
    caption = HOOK_CAPTION.get(lang, HOOK_CAPTION["en"])
    menu    = main_menu(lang)
    sent = await send_pic(context.bot, chat_id, "start", caption, lang, reply_markup=menu)
    if not sent and os.path.exists(HOOK_IMAGE):
        try:
            with open(HOOK_IMAGE, "rb") as p:
                await context.bot.send_photo(chat_id=chat_id, photo=p, caption=caption,
                                             parse_mode=ParseMode.HTML, reply_markup=menu)
        except Exception as e:
            logger.warning(f"Hook image fallback: {e}")
    append_history(user.id, "assistant", caption)
    logger.info(f"/start user={user.id} lang={lang} (tg={user.language_code})")


# ── Menu shortcuts ────────────────────────────────────────────────────────────

async def _menu(action, update, context):
    user = update.effective_user
    u    = get_user(user.id)
    lang = u.get("lang", _detect_lang(user.language_code))
    try:
        await handle_menu_action(context.bot, user.id, update.effective_chat.id, lang, action)
    except Exception as e:
        logger.error(f"_menu crashed action={action} user={user.id}: {e}", exc_info=True)
        err = {"ru": "⚠️ Что-то пошло не так — попробуй ещё раз.",
               "es": "⚠️ Algo salió mal — intentá de nuevo."}.get(lang, "⚠️ Something went wrong — try again.")
        try:
            await update.message.reply_text(err)
        except Exception:
            pass

async def cmd_live(u, c):  await _menu("live",  u, c)
async def cmd_today(u, c): await _menu("today", u, c)
async def cmd_picks(u, c): await _menu("picks", u, c)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u    = get_user(user.id)
    lang = u.get("lang", _detect_lang(user.language_code))
    if user.id in _admin_ids():
        from storage import get_all_users
        users  = get_all_users()
        counts = {}
        for usr in users:
            s = usr.get("state", "unknown")
            counts[s] = counts.get(s, 0) + 1
        lines = ["Datazo Funnel Stats\n"]
        for st, cnt in sorted(counts.items()):
            lines.append(f"{st}: {cnt}")
        lines.append(f"\nTotal: {len(users)}")
        await update.message.reply_text("\n".join(lines))
        return
    await handle_menu_action(context.bot, user.id, update.effective_chat.id, lang, "stats")


# ── Admin: /apitest ───────────────────────────────────────────────────────────

async def cmd_apitest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in _admin_ids():
        return
    await update.message.reply_text("Testing HorseRacing API... check Railway logs for details.")

    from racing import get_live_races, get_today_races, _get, _events, LIVE_RACES_PATH, RACES_PATH
    rapidapi_key = os.environ.get("RAPIDAPI_KEY", "")

    lines = [
        "API Test Results",
        "",
        "Env vars:",
        "RAPIDAPI_KEY: " + ("SET (" + rapidapi_key[:8] + "...)" if rapidapi_key else "MISSING"),
        "",
        "Connectivity:",
    ]

    for name, coro in [("Live races", get_live_races()), ("Today's card", get_today_races())]:
        try:
            races, is_mock = await coro
            status = "REAL DATA" if not is_mock else "MOCK (API failed / key missing)"
            lines.append(f"{name}: {status} — {len(races)} races")
            if races and not is_mock:
                r0 = races[0]
                lines.append(f"  e.g. {r0['course']} — {r0['race_name']} ({r0['n_runners']} runners, fav: {r0['favourite']})")
        except Exception as e:
            lines.append(f"{name}: ERROR — {e}")

    # Raw structure dump — helps verify runner field mapping on the live plan
    lines.append("")
    lines.append("Raw structure probe:")
    for ep in (LIVE_RACES_PATH, RACES_PATH):
        try:
            raw = await _get(ep)
            if raw is None:
                lines.append(f"  {ep}: None (failed/blocked)")
                continue
            events = _events(raw)
            lines.append(f"  {ep}: OK — {len(events)} events")
            if events:
                e0 = events[0]
                lines.append(f"    event keys: {list(e0.keys())[:14]}")
                markets = e0.get("ma") or e0.get("markets") or []
                if markets:
                    m0 = markets[0]
                    lines.append(f"    market keys: {list(m0.keys())[:10]}")
                    parts = m0.get("pa") or m0.get("participants") or m0.get("na") or []
                    if parts and isinstance(parts[0], dict):
                        lines.append(f"    runner keys: {list(parts[0].keys())[:12]}")
                        lines.append(f"    runner sample: {str(parts[0])[:160]}")
        except Exception as e:
            lines.append(f"  {ep}: ERROR {e}")

    from media import pics_available
    lines.append("")
    lines.append("Images (pics/):")
    for moment, ok in pics_available().items():
        lines.append(f"  {moment}: {'OK' if ok else 'MISSING'}")

    # Telegram message limit safety
    text = "\n".join(lines)
    await update.message.reply_text(text[:4000])


# ── Admin: /signal ────────────────────────────────────────────────────────────

async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in _admin_ids():
        return
    from signals import broadcast_daily_signal
    await broadcast_daily_signal(context.bot)
    await update.message.reply_text("Broadcast sent.")


# ── /policy ───────────────────────────────────────────────────────────────────

POLICY_URL = os.environ.get("POLICY_URL", "https://datazo.example.com/privacy")

async def cmd_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u    = get_user(update.effective_user.id)
    lang = u.get("lang", _detect_lang(update.effective_user.language_code))
    body = {
        "ru": ("🔒 *Политика конфиденциальности*\n\n"
               "Datazo собирает только твой Telegram ID для персонализации анализа.\n"
               "Мы не храним платёжные данные.\n\n"
               f"[Полная версия →]({POLICY_URL})"),
        "es": ("🔒 *Política de Privacidad*\n\n"
               "Datazo recopila solo tu ID de Telegram para personalizar el análisis.\n"
               "No almacenamos datos de pago.\n\n"
               f"[Leer política completa →]({POLICY_URL})"),
    }.get(lang, ("🔒 *Privacy Policy*\n\n"
                 "Datazo collects only your Telegram ID to personalise analysis.\n"
                 "We don't store payment data.\n\n"
                 f"[Read full policy →]({POLICY_URL})"))
    await update.message.reply_text(body, parse_mode="Markdown", disable_web_page_preview=True)


# ── Admin: /record ────────────────────────────────────────────────────────────

async def cmd_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in _admin_ids():
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: /record <tag> <correct|wrong>")
        return
    from predictions import record_result
    record_result(args[0], args[1].lower() == "correct")
    await update.message.reply_text(f"Recorded: {args[0]} -> {args[1]}")


# ── Text ──────────────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        return
    u    = get_user(user.id)
    lang = u.get("lang", _detect_lang(user.language_code))
    try:
        await handle_message(context.bot, user.id, update.effective_chat.id, text, lang)
    except Exception as e:
        logger.error(f"handle_text crashed user={user.id}: {e}", exc_info=True)
        err = {"ru": "⚠️ Что-то пошло не так — попробуй ещё раз.",
               "es": "⚠️ Algo salió mal — intentá de nuevo."}.get(lang, "⚠️ Something went wrong — try again.")
        try:
            await update.message.reply_text(err)
        except Exception:
            pass


# ── Post-init ─────────────────────────────────────────────────────────────────

async def post_init(application: Application):
    asyncio.create_task(run_signal_scheduler(application.bot))
    await resume_pending_repeats(application.bot)
    from telegram import BotCommand
    await application.bot.set_my_commands([
        BotCommand("start",  "Start / reset"),
        BotCommand("live",   "Live races"),
        BotCommand("today",  "Today's card"),
        BotCommand("picks",  "Today's tips"),
        BotCommand("stats",  "Track record"),
        BotCommand("policy", "Privacy policy"),
    ])
    logger.info("Datazo Bot started")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("live",    cmd_live))
    app.add_handler(CommandHandler("today",   cmd_today))
    app.add_handler(CommandHandler("picks",   cmd_picks))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("signal",  cmd_signal))
    app.add_handler(CommandHandler("policy",  cmd_policy))
    app.add_handler(CommandHandler("record",  cmd_record))
    app.add_handler(CommandHandler("apitest", cmd_apitest))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info(f"Starting {BOT_USERNAME}...")

    async def _error_handler(update, context):
        from telegram.error import Conflict, NetworkError
        if isinstance(context.error, (Conflict, NetworkError)):
            logger.warning(f"Recoverable error: {context.error}")
            return
        logger.exception(context.error)

    app.add_error_handler(_error_handler)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
