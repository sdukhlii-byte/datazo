"""
onboarding.py — Datazo by Coinplay

2-step conversational onboarding. Valentina asks, AI extracts structured
preferences from any answer in any language.

Step 1: Racing regions  (UK/IRE, France, LATAM/Argentina, USA, Australia)
Step 2: Bet style + favourite tracks (win / each-way / value / favourites)

After step 2 → save preferences → bridge to Coinplay.

Preferences power: daily tip filtering, AI personalization, Mini App.
"""
import json, logging
import httpx
from config import ANTHROPIC_KEY, AI_MODEL
from storage import get_user, update_preferences

logger = logging.getLogger(__name__)
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ── Onboarding questions (step 1 is asked in /start hook already) ─────────────
QUESTIONS = {
    "en": [
        # Step 1
        ("🌍 *Which racing do you follow most?*\n\n"
         "UK & Ireland, France, LATAM, the US… or all of it. Just tell me in your own words."),
        # Step 2
        ("Love it. *How do you like to play them?*\n\n"
         "Win bets, each-way for the value, backing favourites, or chasing the bigger prices? "
         "And any tracks you love?"),
    ],
    "ru": [
        # Step 1
        ("🌍 *Какие скачки смотришь чаще всего?*\n\n"
         "Британия и Ирландия, Франция, ЛАТАМ, США… или всё подряд. Просто расскажи своими словами."),
        # Step 2
        ("Класс. *Как любишь играть?*\n\n"
         "Чистый Win, each-way ради value, ставки на фаворитов или ловишь большие коэффициенты? "
         "И есть любимые ипподромы?"),
    ],
    "es": [
        # Step 1
        ("🌍 *¿Qué hípica seguís más?*\n\n"
         "LATAM, UK e Irlanda, Francia, USA… o todo. Contame como quieras."),
        # Step 2
        ("Me encanta. *¿Cómo te gusta jugarlas?*\n\n"
         "Apuestas al ganador, each-way por el value, ir a los favoritos o buscar las cuotas más altas? "
         "¿Y algún hipódromo favorito?"),
    ],
}

DONE_MSG = {
    "en": ("🏇 *Sorted — your profile's set.*\n\n"
           "I'll filter my daily tips and alerts to what you actually follow. No noise.\n\n"
           "Now — how I actually turn these reads into returns 👇"),
    "ru": ("🏇 *Готово — профиль настроен.*\n\n"
           "Буду фильтровать пики и алерты под то, что ты реально смотришь. Без шума.\n\n"
           "А теперь — как я превращаю эти разборы в результат 👇"),
    "es": ("🏇 *Listo — perfil configurado.*\n\n"
           "Voy a filtrar mis pronósticos y alertas a lo que realmente seguís. Sin ruido.\n\n"
           "Ahora — cómo convierto estas lecturas en ganancia 👇"),
}


async def extract_preferences(user_message: str, step: int, lang: str) -> dict:
    step_context = {
        0: "User answered about which racing regions/countries they follow.",
        1: "User answered about which racing regions/countries they follow.",
        2: "User answered about bet style (win/each-way/value/favourites) and favourite tracks.",
    }.get(step, "")

    prompt = f"""Extract horse-racing preferences from this user message.
Context: {step_context}
Message: "{user_message}"

Return ONLY valid JSON with any of these fields that are mentioned:
{{
  "regions": ["UK & Ireland" | "France" | "Argentina" | "LATAM" | "USA" | "Australia" | other region strings],
  "tracks": ["course / hipódromo names, e.g. Ascot, San Isidro, Longchamp"],
  "bet_style": "win" | "each_way" | "value" | "favourites" | "all" | null,
  "experience": "new" | "casual" | "sharp" | null
}}

Rules:
- Only include fields actually mentioned
- Normalize: "uk"/"british"/"ireland" → "UK & Ireland"; "argentina"/"latam"/"sudamerica" → "LATAM"; "usa"/"states" → "USA"
- "win only" → bet_style "win"; "each way"/"ew"/"placed" → "each_way"; "value"/"odds"/"longshots"/"big prices" → "value"; "favourites"/"favs" → "favourites"; "everything" → "all"
- Beginner/new → experience "new"; experienced/pro → experience "sharp"
- Return empty object {{}} if nothing extractable
- NO markdown, NO explanation, ONLY the JSON object"""

    headers = {
        "x-api-key":         ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model": AI_MODEL, "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Preference extraction error: {e}")
        return {}


async def process_onboarding_answer(user_id: int, user_message: str, step: int, lang: str) -> tuple[str | None, bool]:
    prefs = await extract_preferences(user_message, step, lang)
    if prefs:
        u = get_user(user_id)
        existing = u.get("preferences", {})
        merged = {}
        for field in ("bet_style", "experience"):
            merged[field] = prefs.get(field) or existing.get(field)
        for field in ("regions", "tracks"):
            old = existing.get(field) or []
            new = prefs.get(field) or []
            merged[field] = list(dict.fromkeys(old + new))
        update_preferences(user_id, **merged)
        logger.info(f"User {user_id} prefs updated step={step}: {merged}")

    next_step = step + 1
    questions = QUESTIONS.get(lang, QUESTIONS["en"])
    if next_step < len(questions):
        return questions[next_step], False
    return None, True


def get_first_question(lang: str) -> str:
    return QUESTIONS.get(lang, QUESTIONS["en"])[0]


def format_preferences_summary(prefs: dict, lang: str) -> str:
    def label(en, ru, es):
        return {"en": en, "ru": ru, "es": es}.get(lang, en)
    parts = []
    if prefs.get("regions"):
        parts.append(f"{label('Regions','Регионы','Regiones')}: *{', '.join(prefs['regions'])}*")
    if prefs.get("tracks"):
        parts.append(f"{label('Tracks','Ипподромы','Hipódromos')}: *{', '.join(prefs['tracks'])}*")
    if prefs.get("bet_style"):
        parts.append(f"{label('Style','Стиль','Estilo')}: *{prefs['bet_style']}*")
    if prefs.get("experience"):
        parts.append(f"{label('Level','Уровень','Nivel')}: *{prefs['experience']}*")
    if not parts:
        return ""
    header = label("📋 *Your profile:*\n", "📋 *Твой профиль:*\n", "📋 *Tu perfil:*\n")
    return header + "\n".join(f"• {p}" for p in parts)
