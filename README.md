# Datazo Bot — Coinplay Affiliate (Horse Racing)

Telegram bot for Coinplay affiliate traffic, reworked for **horse racing**.
Persona: **Valentina** — charismatic turf / hípica analyst.
Languages: **EN / RU / ES** — auto-detected from the Telegram `language_code`.
Primary GEO focus: Spanish-speaking (LATAM + ES), plus EN (UK/IRE/INT) and RU (CIS).

Data source: **Bet365 HorseRacing Win/EachWay (PulseScore)** via RapidAPI.

## Funnel

```
/start → HOOK (Valentina intro + region question)
       → ONBOARDING (2 exchanges: regions → bet style/tracks)
       → BRIDGE (natural Coinplay intro)
       → CONVERTING (registration link + button)
       → FTD confirmed
       → REPEAT machine (r1h → r6h → r24h → r3d → r7d)
```

## Environment Variables (Railway / Render)

| Var | Required | Notes |
|-----|----------|-------|
| `BOT_TOKEN` | ✅ | From @BotFather |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key |
| `RAPIDAPI_KEY` | ✅ | RapidAPI key — Bet365 HorseRacing |
| `HORSERACING_API_HOST` | ⚠️ | default `bet365-horseracing-win-eachway.p.rapidapi.com` |
| `LIVE_RACES_PATH` | ⚠️ | default `/sports/horse-racing/live-races` |
| `RACES_PATH` | ⚠️ | default `/sports/horse-racing/races` (racecard) |
| `COINPLAY_URL` | ⚠️ | Ref link |
| `COINPLAY_REG_URL` | ⚠️ | Reg ref link |
| `PERSONA_NAME` | ⚠️ | default `Valentina` |
| `BOT_USERNAME` | ⚠️ | e.g. `DatazoBot` |
| `ADMIN_IDS` | ⚠️ | Comma-separated Telegram user IDs |
| `POLICY_URL` | ⚠️ | Privacy policy URL (Mini App `/privacy`) |
| `DB_PATH` | ⚠️ | Storage file path (default `users.json`) |
| `PORT` | ⚠️ | Mini App API port (default 8080) |
| `MINI_APP_ORIGIN` | ⚠️ | CORS origin for the Mini App (default `*`) |

## Admin Commands

- `/apitest` — test the HorseRacing API + **dump the raw event/market/runner keys**
  so you can confirm the field mapping on your RapidAPI plan.
- `/signal` — manually trigger the evening tips broadcast
- `/stats` — funnel breakdown by state
- `/record <tag> <correct|wrong>` — record a tip result (builds the track record)

## ⚠️ IMPORTANT — verify runner field mapping

The `live-races` endpoint shape is confirmed: `data.events[]`, with each race
carrying `CC` (course), `eventName`, and `ma[]` (markets). The **runner** objects
inside `ma[].pa[]` use Bet365 short codes that can vary by plan. The parser in
`racing.py` (`_parse_runners`) tries the common variants (`NA`/`name`, `OD`/`odds`,
`NO`/`number`, `JN`/`jockey`) and never crashes on a missing field.

After deploying, run `/apitest` as an admin — it prints the actual `runner keys`
and a sample. If odds/names land in different keys, add them to the `_first(...)`
calls in `_parse_runners`. Two-minute fix, no structural changes.

## Mini App HTTP API (api.py)

```
GET /api/health
GET /api/live      → { races: [ {course, race_name, runners[], favourite, ...} ] }
GET /api/upcoming  → { races: [...] }            (today's card)
GET /api/picks?lang=en|ru|es → { picks, stats, source }
GET /api/stats     → Valentina's track record
```

## Daily Schedule (UTC)

- 09:00 — Morning card (today's races, filtered by favourite tracks)
- 18:00 — Evening tips (Valentina's picks)
- Repeat FTD: r1h → r6h → r24h → r3d → r7d

## Moderation Notes (Telegram Ads)

✅ Clean for ads: `/start` hook is racing-analytics framing only; no gambling
keywords in first contact. Coinplay introduced only after warmup (bridge).
⚠️ Bridge message contains bonus/sportsbook — only shown post-warmup, never in
the ad destination.
