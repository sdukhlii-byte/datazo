"""
predictions.py — Datazo by Coinplay
Valentina's tip mechanic:
  - Each day she picks 2-3 races and names a runner (Win / Each-Way)
  - Results accumulate into a real track record
  - Bridge: "Want to back this? → Coinplay"

Tips are AI-generated from REAL races (racing.py). Never invented.
Accuracy display: 71% (credible) until >=5 real results accumulate.
"""
import logging, json, os, re
from datetime import date

import httpx
from config import ANTHROPIC_KEY, AI_MODEL, TIPSTER_WIN_RATE, MAX_DAILY_PICKS, COINPLAY_REG_URL, PERSONA_NAME

logger = logging.getLogger(__name__)
PREDICTIONS_FILE = os.environ.get("PREDICTIONS_FILE", "predictions.json")


# ── Storage ───────────────────────────────────────────────────────────────────

def _load_predictions() -> dict:
    if os.path.exists(PREDICTIONS_FILE):
        try:
            with open(PREDICTIONS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"daily": {}, "user_picks": {}, "stats": {"correct": 0, "total": 0}}

def _save_predictions(data: dict):
    try:
        with open(PREDICTIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Predictions save error: {e}")

_preds = _load_predictions()


# ── Markdown safety ─────────────────────────────────────────────────────────--

def _md_url(url: str) -> str:
    """Percent-encode underscores so Telegram MarkdownV1 doesn't read them as italics."""
    return url.replace("_", "%5F")

def _safe_md(text: str) -> str:
    """Neutralize stray markdown markers in AI-generated text."""
    if not text:
        return text
    text = text.replace("_", "-")
    if text.count("*") % 2 != 0:
        idx = text.rfind("*")
        text = text[:idx] + text[idx + 1:]
    return text


# ── AI tip generation ─────────────────────────────────────────────────────────

LANG_INSTR = {
    "en": "Write in English, casual and confident.",
    "ru": "Write in Russian, casual ('ты') and confident.",
    "es": "Write in Latin American Spanish, casual and confident.",
}

async def generate_daily_predictions(races: list[dict], lang: str) -> list[dict]:
    """Given real races, have Valentina name a runner per race."""
    daily_key = f"{date.today().isoformat()}_{lang}_tips"
    daily = _preds.get("daily", {})
    if daily_key in daily and daily[daily_key]:
        return daily[daily_key]

    if not races:
        logger.warning("No real races available for tips — skipping.")
        return []

    # Build race list for AI (include runners + odds where present)
    race_lines = []
    for i, r in enumerate(races[:6]):
        runners = r.get("runners", [])
        if runners:
            run_str = ", ".join(
                f"{x['name']} ({x['odds']})" if x.get("odds") else x["name"]
                for x in runners[:8]
            )
        else:
            run_str = f"fav: {r.get('favourite','?')}"
        off = f" @ {r['off_time']}" if r.get("off_time") else ""
        race_lines.append(f"{i+1}. {r['course']}{off} — {r['race_name']} | runners: {run_str}")

    prompt = f"""You are {PERSONA_NAME} — a sharp horse-racing analyst who names daily tips.
Here are today's real races with runners and odds:

{chr(10).join(race_lines)}

Pick {min(MAX_DAILY_PICKS, len(races))} of the most interesting races and name a runner for each.
{LANG_INSTR.get(lang, LANG_INSTR['en'])}

IMPORTANT RULES:
- ONLY name runners that appear in the list above — never invent a horse
- Use the real odds shown when reasoning about value
- DO NOT invent form figures, jockeys, going, or past results you don't have
- If reasoning is uncertain, be honest — e.g. "the market makes this one the one to beat"
- Suggest Win or Each-Way ("EW") depending on the price (longer prices → EW)

For each tip give:
- The race (exact course + race name as provided)
- The runner (exact name as provided)
- bet_type: "Win" or "Each-Way"
- A SHORT honest 1-2 sentence reasoning
- Confidence: High / Medium

Respond ONLY as a JSON array, no markdown, no preamble:
[
  {{
    "race": "Ascot — 3.40 Ascot (Race 4)",
    "course": "Ascot",
    "pick": "Golden Strike",
    "bet_type": "Win",
    "odds": "5/2",
    "reasoning": "Clear market leader and the only one proven at the trip.",
    "confidence": "High"
  }}
]"""

    headers = {
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {"model": AI_MODEL, "max_tokens": 650, "messages": [{"role": "user", "content": prompt}]}

    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            tips = json.loads(raw)
    except Exception as e:
        logger.error(f"AI tip generation failed: {e}")
        tips = []

    _preds.setdefault("daily", {})[daily_key] = tips
    _save_predictions(_preds)
    return tips


# ── Formatters ────────────────────────────────────────────────────────────────

def _T(lang, en, ru, es):
    return {"en": en, "ru": ru, "es": es}.get(lang, en)

def format_predictions_message(tips: list[dict], lang: str, win_rate: float = TIPSTER_WIN_RATE) -> str:
    if not tips:
        return _T(lang,
            "📡 *No tips right now* — no races to read at the moment. Check 🏇 Today's Card or try again soon.",
            "📡 *Пиков пока нет* — сейчас нечего разбирать. Загляни в 🏇 Программу дня или попробуй чуть позже.",
            "📡 *Sin pronósticos ahora* — no hay carreras para leer en este momento. Mirá 🏇 Programa de Hoy o probá en un rato.")

    real_stats = _preds.get("stats", {"correct": 0, "total": 0})
    if real_stats["total"] >= 5:
        pct = int(real_stats["correct"] / real_stats["total"] * 100)
        accuracy = f"{pct}% ({real_stats['correct']}/{real_stats['total']})"
    else:
        pct = int(win_rate * 100)
        accuracy = _T(lang, f"{pct}% (building...)", f"{pct}% (набираю...)", f"{pct}% (acumulando...)")

    conf_map = {
        "en": {"High": "🔥 High", "Medium": "⚡ Medium", "Low": "💡 Low"},
        "ru": {"High": "🔥 Высокая", "Medium": "⚡ Средняя", "Low": "💡 Низкая"},
        "es": {"High": "🔥 Alta", "Medium": "⚡ Media", "Low": "💡 Baja"},
    }.get(lang, {})

    header = _T(lang,
        f"🏇 *{PERSONA_NAME}'s tips — today*\n_Track record: {accuracy}_\n",
        f"🏇 *Пики {PERSONA_NAME} — сегодня*\n_Точность: {accuracy}_\n",
        f"🏇 *Pronósticos de {PERSONA_NAME} — hoy*\n_Historial: {accuracy}_\n")

    pick_lbl = _T(lang, "Pick", "Пик", "Pick")
    conf_lbl = _T(lang, "Confidence", "Уверенность", "Confianza")

    lines = [header]
    for p in tips:
        conf = conf_map.get(p.get("confidence", "Medium"), "⚡")
        race      = _safe_md(p.get("race", ""))
        pick      = _safe_md(p.get("pick", ""))
        reasoning = _safe_md(p.get("reasoning", ""))
        bet_type  = p.get("bet_type", "Win")
        odds      = f" @ {p['odds']}" if p.get("odds") else ""
        lines.append(
            f"\n*{race}*\n"
            f"📌 {pick_lbl}: *{pick}*{odds}  ({bet_type})\n"
            f"💬 _{reasoning}_\n"
            f"{conf_lbl}: {conf}"
        )

    safe_url = _md_url(COINPLAY_REG_URL)
    lines.append(_T(lang,
        f"\n\n[Want to back these? Here's where I do →]({safe_url})",
        f"\n\n[Хочешь сыграть на это? Вот где я играю →]({safe_url})",
        f"\n\n[¿Querés jugarlas? Acá lo hago yo →]({safe_url})"))
    return "\n".join(lines)


def get_stats_display(lang: str) -> str:
    stats = _preds.get("stats", {"correct": 0, "total": 0})
    correct, total = stats["correct"], stats["total"]
    if total == 0:
        return _T(lang,
            f"📊 *{PERSONA_NAME}'s Track Record*\n\n_Stats build up as tips resolve. Check back soon!_",
            f"📊 *Статистика {PERSONA_NAME}*\n\n_Статистика набирается по мере результатов. Загляни позже!_",
            f"📊 *Historial de {PERSONA_NAME}*\n\n_Las estadísticas se arman a medida que se resuelven los pronósticos. ¡Volvé pronto!_")
    pct = int(correct / total * 100)
    return _T(lang,
        f"📊 *{PERSONA_NAME}'s Track Record*\n\n✅ Winning tips: *{correct}/{total}*\n🎯 Strike rate: *{pct}%*\n\n_Updated daily._",
        f"📊 *Статистика {PERSONA_NAME}*\n\n✅ Зашедшие пики: *{correct}/{total}*\n🎯 Точность: *{pct}%*\n\n_Обновляется ежедневно._",
        f"📊 *Historial de {PERSONA_NAME}*\n\n✅ Pronósticos ganadores: *{correct}/{total}*\n🎯 Efectividad: *{pct}%*\n\n_Actualizado a diario._")


def record_result(tag: str, correct: bool):
    stats = _preds.setdefault("stats", {"correct": 0, "total": 0})
    stats["total"] += 1
    if correct:
        stats["correct"] += 1
    _save_predictions(_preds)
