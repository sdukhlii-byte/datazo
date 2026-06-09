"""
config.py — Datazo by Coinplay
Telegram bot: live horse-racing + AI tips (Valentina) → Coinplay FTD

Persona: Valentina — charismatic turf / hípica analyst.
Languages: EN / RU / ES  (auto-detected from Telegram language_code).
Primary GEO focus: Spanish-speaking (LATAM + ES), plus EN (UK/IRE/INT) and RU (CIS).
"""
import os

# ── Core credentials ──────────────────────────────────────────────────────────
BOT_TOKEN     = os.environ["BOT_TOKEN"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
BOT_USERNAME  = os.environ.get("BOT_USERNAME", "DatazoBot")

# ── External APIs ─────────────────────────────────────────────────────────────
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")   # RapidAPI key (shared)

# Bet365 HorseRacing Win/EachWay (PulseScore) — RapidAPI
# https://rapidapi.com/pulsescore/api/bet365-horseracing-win-eachway
HORSERACING_API_HOST = os.environ.get(
    "HORSERACING_API_HOST",
    "bet365-horseracing-win-eachway.p.rapidapi.com",
)
# Endpoint paths — confirmed: /sports/horse-racing/live-races
# "Get Races" path is a sane default; override via env if the provider differs.
LIVE_RACES_PATH = os.environ.get("LIVE_RACES_PATH", "/sports/horse-racing/live-races")
RACES_PATH      = os.environ.get("RACES_PATH",      "/sports/horse-racing/races")

# ── AI settings ───────────────────────────────────────────────────────────────
AI_MODEL      = "claude-sonnet-4-20250514"
AI_MAX_TOKENS = 320

# ── Coinplay affiliate link (unchanged) ───────────────────────────────────────
COINPLAY_URL     = os.environ.get("COINPLAY_URL",     "https://promotioncoinplay.com/L?tag=d_5617175m_59419c_&site=5617175&ad=59419")
COINPLAY_REG_URL = os.environ.get("COINPLAY_REG_URL", "https://promotioncoinplay.com/L?tag=d_5617175m_59419c_&site=5617175&ad=59419")

# ── Offer details ─────────────────────────────────────────────────────────────
OFFER = {
    "bonus_pct":    100,
    "bonus_max":    5000,
    "free_spins":   80,
    "min_deposit":  20,
    "wagering":     40,
    "cashback_pct": 5,
    "currencies":   40,
}

# ── Persona ───────────────────────────────────────────────────────────────────
PERSONA_NAME = os.environ.get("PERSONA_NAME", "Valentina")

# ── Racing regions tracked (for personalization) ──────────────────────────────
RACING_REGIONS = [
    "UK & Ireland", "France", "Argentina", "USA", "Australia",
]

# ── Predictions config ────────────────────────────────────────────────────────
TIPSTER_WIN_RATE = 0.71   # displayed accuracy until real stats accumulate
MAX_DAILY_PICKS  = 3      # max tips per broadcast
ONBOARDING_TURNS = 2      # AI exchanges before onboarding ends

# ── Language detection ────────────────────────────────────────────────────────
# Telegram language_code → bot language
TG_LANG_MAP = {
    "en": "en",
    "ru": "ru",
    "uk": "ru",   # Ukrainian users → Russian bot (closest available)
    "be": "ru",
    "es": "es",
    "pt": "es",   # Portuguese → Spanish (closest LATAM fit)
}

SUPPORTED_LANGS = {"en", "ru", "es"}
DEFAULT_LANG    = "en"

# ── Funnel states ─────────────────────────────────────────────────────────────
class State:
    NEW        = "new"
    WARMUP     = "warmup"
    BRIDGE     = "bridge"
    CONVERTING = "converting"
    DEPOSITED  = "deposited"
    REPEAT     = "repeat"

# ── Repeat FTD schedule (seconds) ─────────────────────────────────────────────
REPEAT_SCHEDULE = [
    3_600,       # r1h
    21_600,      # r6h
    86_400,      # r24h
    259_200,     # r3d
    604_800,     # r7d
]

# ── Storage / media ───────────────────────────────────────────────────────────
DB_PATH    = os.environ.get("DB_PATH", "users.json")
HOOK_IMAGE = os.environ.get("HOOK_IMAGE", "hook.png")
