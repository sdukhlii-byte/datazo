"""
ai_agent.py — Datazo by Coinplay

Persona: Valentina — charismatic horse-racing analyst.
Preferences injected into every prompt for personalization.
Anti-hallucination: only real race data passed, never mock.
"""
import logging, re
import httpx
from config import ANTHROPIC_KEY, AI_MODEL, AI_MAX_TOKENS, OFFER, COINPLAY_REG_URL, PERSONA_NAME

logger = logging.getLogger(__name__)
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

INTENT_RE  = re.compile(r'\[INTENT:([^\]]+)\]')
BARRIER_RE = re.compile(r'\[BARRIER:([^\]]+)\]')
STAGE_RE   = re.compile(r'\[NEXT:([^\]]+)\]')

LANG_INSTR = {
    "en": "Respond in English (casual, sharp, confident).",
    "ru": "Respond in Russian (casual 'ты', sharp, confident).",
    "es": "Respond in Latin American Spanish (casual 'vos/tú', sharp, confident).",
}


def _prefs_str(prefs: dict) -> str:
    if not prefs or not any(prefs.values()):
        return "No preferences collected yet."
    parts = []
    if prefs.get("regions"):
        parts.append(f"Regions: {', '.join(prefs['regions'])}")
    if prefs.get("tracks"):
        parts.append(f"Favourite tracks: {', '.join(prefs['tracks'])}")
    if prefs.get("bet_style"):
        parts.append(f"Bet style: {prefs['bet_style']}")
    if prefs.get("experience"):
        parts.append(f"Experience: {prefs['experience']}")
    return " | ".join(parts)


def _race_ctx(real_live: list, real_upcoming: list) -> str:
    if not real_live and not real_upcoming:
        return "NO RACE DATA AVAILABLE — do not invent any races, horses, courses, or odds."
    lines = []
    if real_live:
        lines.append("LIVE NOW (real):")
        for r in real_live[:4]:
            runners = ", ".join(f"{x['name']} {x.get('odds','')}".strip() for x in r.get("runners", [])[:5])
            lines.append(f"  {r['course']} — {r['race_name']} | runners: {runners}")
    if real_upcoming:
        lines.append("TODAY'S CARD (real):")
        for r in real_upcoming[:8]:
            off = f" @ {r['off_time']}" if r.get("off_time") else ""
            fav = f" | fav: {r['favourite']}" if r.get("favourite") else ""
            lines.append(f"  {r['course']}{off} — {r['race_name']}{fav}")
    return "\n".join(lines)


def _assistant_system(lang: str, state: str, prefs: dict, real_live: list, real_upcoming: list) -> str:
    lang_instr = LANG_INSTR.get(lang, LANG_INSTR["en"])
    offer = (
        f"100% bonus up to {OFFER['bonus_max']} USDT + {OFFER['free_spins']} free spins, "
        f"min {OFFER['min_deposit']} USDT, {OFFER['cashback_pct']}% cashback, 40+ cryptos"
    )
    return f"""You are {PERSONA_NAME} — a charismatic, confident horse-racing (turf/hípica) analyst running the Datazo Telegram channel.
You have real personality: warm, playful, but razor-sharp on form, going (track condition), the draw, jockeys and trainers.
You use Coinplay (coinplay.com) to back your reads.
{lang_instr}

USER PROFILE (personalize to this):
{_prefs_str(prefs)}

REAL RACE DATA (ONLY reference these — never invent):
{_race_ctx(real_live, real_upcoming)}

COINPLAY: {offer} | {COINPLAY_REG_URL} | Curacao licensed, since 2022

ANTI-HALLUCINATION:
- NEVER invent horse names, courses, race times, odds, jockeys, trainers, or results
- NEVER fabricate form figures or stats you don't actually have
- If no race data → talk racing strategy in general terms ONLY (going, draw bias, each-way value, staking)
- If unsure about a runner's form → say "based on recent runs" not invented numbers

PERSONALIZATION:
- Reference the user's regions/tracks/bet-style when relevant
- LATAM fans → Argentine/South-American turf angles (San Isidro, Palermo)
- UK/IRE fans → going, draw bias, festival meetings
- Tailor examples to their profile

CURRENT STATE: {state}

ROLE:
- Answer questions about racing, form-reading, staking, each-way value, crypto
- Mention Coinplay naturally when relevant — don't push hard
- User has menu buttons for live races / card / tips — don't replicate those
- Keep responses under 150 words

INTENT TAGS (prepend):
[INTENT:racing_fan|platform_curious|deposit_ready|ftd_confirmed|objection|just_browsing]
[NEXT:warmup|bridge|converting|deposited]
"""


async def get_ai_response(
    user_message: str,
    lang: str,
    state: str,
    history: list,
    barriers: list,
    real_live: list = None,
    real_upcoming: list = None,
    prefs: dict = None,
) -> dict:
    system = _assistant_system(lang, state, prefs or {}, real_live or [], real_upcoming or [])
    messages = [{"role": e["role"], "content": e["content"]} for e in history[-12:]]
    messages.append({"role": "user", "content": user_message})

    headers = {
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      AI_MODEL,
        "max_tokens": AI_MAX_TOKENS,
        "system":     system,
        "messages":   messages,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()

        intent  = (INTENT_RE.search(raw)  or type("x",(),{"group":lambda s,i:"just_browsing"})()).group(1)
        barrier = (BARRIER_RE.search(raw) or type("x",(),{"group":lambda s,i:None})()).group(1)
        next_s  = (STAGE_RE.search(raw)   or type("x",(),{"group":lambda s,i:None})()).group(1)
        clean   = STAGE_RE.sub("", BARRIER_RE.sub("", INTENT_RE.sub("", raw))).strip()
        return {"text": clean, "intent": intent, "barrier": barrier, "next": next_s}

    except httpx.TimeoutException:
        logger.error("AI timeout")
        return _fallback(lang)
    except Exception as e:
        logger.error(f"AI error: {e}")
        return _fallback(lang)


def _fallback(lang: str) -> dict:
    txt = {"en": "📡 Give me a sec.", "ru": "📡 Секунду.", "es": "📡 Dame un seg."}.get(lang, "📡 Give me a sec.")
    return {"text": txt, "intent": "just_browsing", "barrier": None, "next": None}


async def detect_ftd(user_message: str, lang: str) -> bool:
    prompt = (
        f'Did this message confirm the user made a deposit or completed registration '
        f'on a gambling/crypto platform?\nMessage: "{user_message}"\nReply only: YES or NO'
    )
    headers = {
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model": AI_MODEL, "max_tokens": 10,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip().upper().startswith("YES")
    except Exception as e:
        logger.error(f"FTD detect: {e}")
        return False
