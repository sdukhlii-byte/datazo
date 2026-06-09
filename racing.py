"""
racing.py — Datazo by Coinplay

Data source: Bet365 HorseRacing Win/EachWay (PulseScore) via RapidAPI.
  Host: bet365-horseracing-win-eachway.p.rapidapi.com
  GET /sports/horse-racing/live-races   → { data: { events: [...] } }   (confirmed)
  GET /sports/horse-racing/races        → { data: { events: [...] } }   (racecard / scheduled)

Race object (normalized shape used everywhere downstream):
  {
    "type":       "race",
    "id":         "2076939751347193392C2A_1_1",
    "course":     "Compiegne",
    "race_name":  "1.18 Compiegne (Race 1)",
    "off_time":   "13:18",                # best-effort from eventName prefix
    "status":     "LIVE 🔴" | "upcoming" | "finished",
    "begin_at":   "2026-06-09T13:18:00+00:00",
    "n_runners":  8,
    "runners": [
       {"name": "Some Horse", "number": 1, "odds": "5/2", "odds_dec": 3.5,
        "jockey": "", "fav": True}
    ],
    "favourite":  "Some Horse",
  }

NOTE ON FIELD NAMES: the participant (runner) object inside ma[].pa[] uses
Bet365 short codes that can vary. The parser below tries the common variants
and never crashes on a missing field. Run /apitest on Railway to dump the raw
keys of the first runner and tighten the mapping if needed.
"""
import asyncio, logging, time, re
from datetime import datetime, timezone
import httpx
from config import (
    RAPIDAPI_KEY, HORSERACING_API_HOST,
    LIVE_RACES_PATH, RACES_PATH,
)

logger = logging.getLogger(__name__)

BASE = f"https://{HORSERACING_API_HOST}"

_cache: dict = {}
CACHE_TTL = 180  # 3 min — racing data moves fast


def _cached(key):
    e = _cache.get(key)
    if e and time.time() - e["ts"] < CACHE_TTL:
        return e["data"]
    return None

def _set_cache(key, data):
    _cache[key] = {"ts": time.time(), "data": data}


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _headers():
    return {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": HORSERACING_API_HOST,
        "Content-Type":    "application/json",
    }

async def _get(path: str, params: dict = {}) -> dict | None:
    if not RAPIDAPI_KEY:
        logger.warning("HorseRacing API: RAPIDAPI_KEY not set")
        return None
    url = f"{BASE}{path}"
    logger.info(f"HorseRacing API → GET {url}")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=_headers(), params=params)
            logger.info(f"HorseRacing API ← {r.status_code} ({len(r.content)} bytes)")
            r.raise_for_status()
            data = r.json()
            return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HorseRacing API HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"HorseRacing API {path} {type(e).__name__}: {e}")
        return None


# ── Parsing helpers ─────────────────────────────────────────────────────────--

def _events(data: dict | None) -> list[dict]:
    """Extract the events array regardless of small wrapper differences."""
    if not isinstance(data, dict):
        return []
    d = data.get("data")
    if isinstance(d, dict):
        ev = d.get("events")
        if isinstance(ev, list):
            return ev
    # Some providers return events at the top level
    ev = data.get("events")
    return ev if isinstance(ev, list) else []


def _first(d: dict, *keys, default=None):
    """Return first present non-empty value among keys (case-insensitive)."""
    if not isinstance(d, dict):
        return default
    lower = {k.lower(): v for k, v in d.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, "", []):
            return v
    return default


_FRAC_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")

def _frac_to_dec(odds: str) -> float | None:
    """'5/2' → 3.5 (decimal). Returns None if unparseable."""
    if not odds:
        return None
    odds = str(odds).strip()
    m = _FRAC_RE.match(odds)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return round(num / den + 1, 2) if den else None
    try:
        v = float(odds)
        return v if v > 1 else None
    except ValueError:
        return None


def _parse_runners(event: dict) -> list[dict]:
    """Pull runners out of ma[] (markets) → pa[] (participants).
    Prefers the 'Win' market. Defensive against varying field names.
    """
    markets = event.get("ma") or event.get("markets") or []
    win_market = None
    for m in markets:
        nm = str(_first(m, "name", "NA", "N", default="")).lower()
        if "win" in nm and "each" not in nm:
            win_market = m
            break
    if win_market is None and markets:
        win_market = markets[0]
    if not win_market:
        return []

    parts = win_market.get("pa") or win_market.get("participants") or win_market.get("na") or []
    runners = []
    for i, p in enumerate(parts):
        if not isinstance(p, dict):
            continue
        name = _first(p, "name", "NA", "N", "runner", default=f"Runner {i+1}")
        odds = _first(p, "OD", "odds", "price", "FB", default="")
        odds = str(odds)
        runners.append({
            "name":     str(name),
            "number":   _first(p, "number", "no", "NO", "saddle", default=i + 1),
            "odds":     odds,
            "odds_dec": _frac_to_dec(odds),
            "jockey":   str(_first(p, "jockey", "JN", "rider", default="")),
            "fav":      False,
        })
    # Mark favourite = shortest decimal odds
    priced = [r for r in runners if r["odds_dec"]]
    if priced:
        fav = min(priced, key=lambda r: r["odds_dec"])
        fav["fav"] = True
    return runners


def _parse_off_time(event: dict) -> str:
    """Best-effort race off-time (HH:MM UTC) from a timestamp field if present.

    NOTE: the eventName prefix (e.g. '1.18' in '1.18 Compiegne (Race 1)') is the
    provider's race index, NOT the off-time, so we do NOT parse time from it.
    Prefer an explicit time/start field; otherwise leave blank.
    """
    ts = _first(event, "startTimestamp", "OFF", "startTime", default=0)
    try:
        ts = int(ts)
        if ts > 1e12:
            ts = ts // 1000
        if ts > 0:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M")
    except (ValueError, TypeError):
        pass
    return ""


def _parse_race(event: dict, status: str) -> dict:
    course    = str(_first(event, "CC", "course", "venue", default=""))
    race_name = str(_first(event, "eventName", "name", default="")) or (course or "Race")
    eid       = str(_first(event, "id", "IID", default=""))
    runners   = _parse_runners(event)
    fav       = next((r["name"] for r in runners if r.get("fav")), "")

    ts = _first(event, "updatedAtUTC", "startTimestamp", default=0)
    begin_at = ""
    try:
        ts = int(ts)
        if ts > 1e12:   # milliseconds
            ts = ts // 1000
        if ts > 0:
            begin_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass

    return {
        "type":      "race",
        "id":        eid,
        "course":    course,
        "race_name": race_name,
        "off_time":  _parse_off_time(event),
        "status":    status,
        "begin_at":  begin_at,
        "n_runners": len(runners),
        "runners":   runners,
        "favourite": fav,
    }


# ── Public getters ──────────────────────────────────────────────────────────--

async def get_live_races() -> tuple[list[dict], bool]:
    """Races in-running right now. Returns (races, is_mock)."""
    key = "races_live"
    cached = _cached(key)
    if cached is not None:
        return cached
    data = await _get(LIVE_RACES_PATH)
    if data is None:
        return _mock_live_races(), True
    races = [_parse_race(e, "LIVE 🔴") for e in _events(data)]
    result = (races, False)
    _set_cache(key, result)
    return result


async def get_today_races() -> tuple[list[dict], bool]:
    """Today's full racecard (scheduled). Falls back to live-races feed if the
    racecard endpoint isn't available on the plan."""
    key = "races_today"
    cached = _cached(key)
    if cached is not None:
        return cached

    data = await _get(RACES_PATH)
    if data is not None:
        races = [_parse_race(e, "upcoming") for e in _events(data)]
        if races:
            result = (races, False)
            _set_cache(key, result)
            return result

    # Fallback: use the live feed (still real data — races coming up shortly)
    data = await _get(LIVE_RACES_PATH)
    if data is None:
        return _mock_today_races(), True
    races = [_parse_race(e, "upcoming") for e in _events(data)]
    result = (races, False)
    _set_cache(key, result)
    return result


async def get_recent_results(limit: int = 6) -> tuple[list[dict], bool]:
    # The Win/EachWay feed doesn't expose settled results cleanly — keep empty.
    return [], True


# ── Combined context for AI + display ─────────────────────────────────────────

async def fetch_race_context() -> dict:
    (live, mock_live), (today, mock_today) = await asyncio.gather(
        get_live_races(),
        get_today_races(),
    )
    real_live     = [] if mock_live  else live
    real_upcoming = [] if mock_today else today

    has_real_live     = not mock_live
    has_real_upcoming = not mock_today

    display_live     = real_live     if has_real_live     else live
    display_upcoming = real_upcoming if has_real_upcoming else today

    return {
        "live":              real_live,
        "upcoming":          real_upcoming,
        "has_real":          bool(real_live or real_upcoming),
        "has_real_live":     has_real_live,
        "has_real_upcoming": has_real_upcoming,
        "for_display": {
            "live":     display_live,
            "upcoming": display_upcoming,
        },
    }


# ── Formatters ─────────────────────────────────────────────────────────────────

def _runners_line(race: dict, limit: int = 4) -> str:
    rs = race.get("runners", [])[:limit]
    if not rs:
        return ""
    bits = []
    for r in rs:
        star = "⭐" if r.get("fav") else ""
        odds = f" {r['odds']}" if r.get("odds") else ""
        bits.append(f"{star}{r['name']}{odds}")
    more = race.get("n_runners", 0) - len(rs)
    tail = f" +{more}" if more > 0 else ""
    return "   _" + " · ".join(bits) + tail + "_"


def _T(lang, en, ru, es):
    return {"en": en, "ru": ru, "es": es}.get(lang, en)


def format_live_races_message(races: list[dict], lang: str, is_mock: bool = False) -> str:
    if is_mock:
        return _T(lang,
            "📡 No live races right now — I'll ping you the moment a card goes off.",
            "📡 Сейчас нет живых забегов — напишу, как только стартует заезд.",
            "📡 No hay carreras en vivo ahora — te aviso apenas largue una.")
    if not races:
        return _T(lang,
            "📡 *Live now:*\n\nAll quiet on the track — nothing under way. Tap 🏇 Today's Card for what's coming.",
            "📡 *Сейчас в эфире:*\n\nНа дорожке тихо — ничего не бежит. Жми 🏇 Программа дня, чтобы увидеть ближайшие.",
            "📡 *En vivo ahora:*\n\nPista tranquila — nada corriendo. Tocá 🏇 Programa de Hoy para ver lo que viene.")
    header = _T(lang, "📡 *Live races:*", "📡 *Живые забеги:*", "📡 *Carreras en vivo:*")
    lines = []
    for r in races[:8]:
        title = f"🔴 *{r['course'] or 'Race'}* — {r['race_name']}"
        runners = _runners_line(r)
        lines.append(title + ("\n" + runners if runners else ""))
    return header + "\n\n" + "\n\n".join(lines)


def format_racecard_message(races: list[dict], lang: str, is_mock: bool = False) -> str:
    if is_mock or not races:
        return _T(lang,
            "🏇 No racecard data yet — check back shortly.",
            "🏇 Программы пока нет — загляни чуть позже.",
            "🏇 Sin programa aún — volvé en un rato.")
    header = _T(lang, "🏇 *Today's card:*", "🏇 *Программа на сегодня:*", "🏇 *Programa de hoy:*")
    lines = []
    for r in races[:10]:
        off = f" @ {r['off_time']}" if r.get("off_time") else ""
        title = f"🕐 *{r['course'] or 'Race'}*{off} — {r['race_name']}"
        fav = f"\n   ⭐ _fav: {r['favourite']}_" if r.get("favourite") else ""
        lines.append(title + fav)
    return header + "\n\n" + "\n\n".join(lines)


def format_results_message(races: list[dict], lang: str, is_mock: bool = False) -> str:
    return _T(lang, "No recent results.", "Нет свежих результатов.", "Sin resultados recientes.")


# ── Mock data (display only — never passed to AI) ─────────────────────────────

def _mock_live_races() -> list[dict]:
    return [
        {"type": "race", "id": "m1", "course": "Ascot", "race_name": "3.40 Ascot (Race 4)",
         "off_time": "15:40", "status": "LIVE 🔴", "begin_at": "", "n_runners": 8,
         "favourite": "Golden Strike",
         "runners": [
            {"name": "Golden Strike", "number": 1, "odds": "5/2", "odds_dec": 3.5, "jockey": "", "fav": True},
            {"name": "Night Runner",  "number": 2, "odds": "4/1", "odds_dec": 5.0, "jockey": "", "fav": False},
            {"name": "Silver Lady",    "number": 3, "odds": "6/1", "odds_dec": 7.0, "jockey": "", "fav": False},
         ]},
    ]

def _mock_today_races() -> list[dict]:
    return [
        {"type": "race", "id": "m2", "course": "Longchamp", "race_name": "2.15 Longchamp (Race 2)",
         "off_time": "14:15", "status": "upcoming", "begin_at": "", "n_runners": 10,
         "favourite": "Vent du Nord", "runners": [
            {"name": "Vent du Nord", "number": 1, "odds": "2/1", "odds_dec": 3.0, "jockey": "", "fav": True},
         ]},
        {"type": "race", "id": "m3", "course": "San Isidro", "race_name": "4.30 San Isidro (Carrera 6)",
         "off_time": "16:30", "status": "upcoming", "begin_at": "", "n_runners": 9,
         "favourite": "Tormenta", "runners": [
            {"name": "Tormenta", "number": 4, "odds": "3/1", "odds_dec": 4.0, "jockey": "", "fav": True},
         ]},
    ]
