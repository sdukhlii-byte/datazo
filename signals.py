"""
signals.py — Datazo by Coinplay
Two broadcasts per day, personalized by preferences.
  09:00 UTC — morning card (today's racecard, filtered by favourite tracks)
  18:00 UTC — evening tips (Valentina's picks, personalized)
"""
import asyncio, logging, time
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode
from config import State, COINPLAY_URL
from storage import get_all_users, update_user
from messages import MORNING_DIGEST_HEADER, MORNING_DIGEST_FOOTER
from racing import fetch_race_context, format_racecard_message
from predictions import generate_daily_predictions, format_predictions_message

logger = logging.getLogger(__name__)

MORNING_HOUR = 9
EVENING_HOUR = 18


def _active_users() -> list[dict]:
    now = time.time()
    return [
        u for u in get_all_users()
        if u.get("state") not in (State.NEW,)
        and now - u.get("last_active", 0) < 7 * 86400
    ]


def _filter_races_by_prefs(races: list, prefs: dict) -> list:
    tracks = [t.lower() for t in prefs.get("tracks", [])]
    if not tracks:
        return races
    matched = [r for r in races if any(t in r.get("course", "").lower() for t in tracks)]
    return matched or races


async def _send_to(bot: Bot, user_id: int, text: str):
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        update_user(user_id, last_signal_at=time.time())
    except Exception as e:
        logger.warning(f"Broadcast failed {user_id}: {e}")


async def broadcast_morning_digest(bot: Bot):
    logger.info("Morning card broadcast...")
    ctx     = await fetch_race_context()
    display = ctx["for_display"]
    is_mock = not ctx["has_real"]

    count = 0
    for u in _active_users():
        lang  = u.get("lang", "en")
        prefs = u.get("preferences", {})
        races = _filter_races_by_prefs(display["upcoming"], prefs)

        header = MORNING_DIGEST_HEADER.get(lang, MORNING_DIGEST_HEADER["en"])
        body   = format_racecard_message(races, lang, is_mock=is_mock)
        footer = MORNING_DIGEST_FOOTER.get(lang, MORNING_DIGEST_FOOTER["en"])
        full   = header + body + footer

        from media import send_pic
        img_sent = await send_pic(bot, u["user_id"], "morning", full, lang)
        if not img_sent:
            await _send_to(bot, u["user_id"], full)
        count += 1
        await asyncio.sleep(0.05)
    logger.info(f"Morning card: {count} users")


async def broadcast_daily_signal(bot: Bot):
    logger.info("Evening tips broadcast...")
    ctx     = await fetch_race_context()

    count = 0
    for u in _active_users():
        lang  = u.get("lang", "en")
        state = u.get("state", State.WARMUP)
        prefs = u.get("preferences", {})

        races = _filter_races_by_prefs(ctx["live"] + ctx["upcoming"], prefs) if ctx["has_real"] else []
        tips  = await generate_daily_predictions(races, lang)
        text  = format_predictions_message(tips, lang)

        if state in (State.CONVERTING, State.REPEAT, State.DEPOSITED):
            text += f"\n\n👉 {COINPLAY_URL}"

        from media import send_pic
        img_sent = await send_pic(bot, u["user_id"], "picks", text, lang)
        if not img_sent:
            await _send_to(bot, u["user_id"], text)
        count += 1
        await asyncio.sleep(0.08)
    logger.info(f"Evening tips: {count} users")


async def run_signal_scheduler(bot: Bot):
    while True:
        now = datetime.now(timezone.utc)
        secs_opts = []
        for h in (MORNING_HOUR, EVENING_HOUR):
            diff = ((h - now.hour) % 24) * 3600 - now.minute * 60 - now.second
            if diff <= 0:
                diff += 86400
            secs_opts.append((diff, h))
        next_secs, next_hour = min(secs_opts)
        logger.info(f"Next broadcast {next_hour:02d}:00 UTC in {next_secs/3600:.1f}h")
        await asyncio.sleep(next_secs)
        if next_hour == MORNING_HOUR:
            await broadcast_morning_digest(bot)
        else:
            await broadcast_daily_signal(bot)
