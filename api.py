"""
api.py — Datazo Mini App HTTP API

Async, stdlib-only. Endpoints:
  GET /api/health
  GET /api/live      → { races: [...] }
  GET /api/upcoming  → { races: [...] }   (today's racecard)
  GET /api/picks?lang=en|ru|es → { picks: [...], stats: {...}, source: ... }
  GET /api/stats     → Valentina's track record
"""
import asyncio, json, logging, os
from urllib.parse import urlparse, parse_qs

from predictions import generate_daily_predictions, _preds
from racing import fetch_race_context, get_live_races, get_today_races

logger = logging.getLogger(__name__)
PORT        = int(os.environ.get("PORT", os.environ.get("API_PORT", 8080)))
CORS_ORIGIN = os.environ.get("MINI_APP_ORIGIN", "*")


def _json_bytes(data) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")

def _cors_headers(body: bytes):
    return [
        ("Content-Type",                 "application/json; charset=utf-8"),
        ("Access-Control-Allow-Origin",  CORS_ORIGIN),
        ("Access-Control-Allow-Methods", "GET, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type"),
        ("Content-Length",               str(len(body))),
    ]


async def handle_health():
    return 200, _json_bytes({"status": "ok"})

async def handle_stats():
    stats   = _preds.get("stats", {"correct": 0, "total": 0})
    total   = stats["total"]; correct = stats["correct"]
    return 200, _json_bytes({
        "correct": correct, "total": total,
        "rate": round(correct / total * 100) if total > 0 else None,
        "note": "accumulating" if total < 5 else "real",
    })

async def handle_live():
    races, _ = await get_live_races()
    return 200, _json_bytes({"races": races})

async def handle_upcoming():
    races, _ = await get_today_races()
    return 200, _json_bytes({"races": races})

async def handle_picks(lang: str):
    ctx   = await fetch_race_context()
    races = (ctx.get("live", []) + ctx.get("upcoming", [])) if ctx.get("has_real") else []
    picks = await generate_daily_predictions(races, lang)
    stats = _preds.get("stats", {"correct": 0, "total": 0})
    total = stats["total"]; correct = stats["correct"]
    return 200, _json_bytes({
        "picks": picks,
        "stats": {
            "correct": correct, "total": total,
            "rate": round(correct / total * 100) if total > 0 else None,
            "note": "accumulating" if total < 5 else "real",
        },
        "source": "real" if races else "no_races",
    })


async def handle_request(reader, writer):
    try:
        raw = await reader.read(4096)
        if not raw:
            writer.close(); return
        first_line = raw.split(b"\r\n")[0].decode("utf-8", errors="replace")
        parts = first_line.split(" ")
        method = parts[0] if parts else "GET"
        full_path = parts[1] if len(parts) > 1 else "/"
        parsed = urlparse(full_path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if method == "OPTIONS":
            writer.write(
                b"HTTP/1.1 204 No Content\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Access-Control-Allow-Methods: GET, OPTIONS\r\n"
                b"Access-Control-Allow-Headers: Content-Type\r\n"
                b"Content-Length: 0\r\n\r\n"
            )
            await writer.drain(); writer.close(); return

        try:
            if path == "/api/health":
                status, body = await handle_health()
            elif path == "/api/stats":
                status, body = await handle_stats()
            elif path == "/api/live":
                status, body = await handle_live()
            elif path == "/api/upcoming":
                status, body = await handle_upcoming()
            elif path == "/api/picks":
                lang = (qs.get("lang", ["en"])[0] or "en").lower()
                if lang not in ("en", "ru", "es"):
                    lang = "en"
                status, body = await handle_picks(lang)
            else:
                status, body = 404, _json_bytes({"error": "not_found"})
        except Exception as e:
            logger.error(f"{path} handler error: {e}", exc_info=True)
            status, body = 500, _json_bytes({"error": "internal_error"})

        headers = _cors_headers(body)
        status_text = {200: "OK", 404: "Not Found", 500: "Internal Server Error"}.get(status, "OK")
        header_lines = "\r\n".join(f"{k}: {v}" for k, v in headers)
        writer.write(f"HTTP/1.1 {status} {status_text}\r\n{header_lines}\r\n\r\n".encode() + body)
        await writer.drain()
        logger.info(f'"{method} {path} HTTP/1.1" {status} -')
    except Exception as e:
        logger.error(f"Request handling error: {e}")
    finally:
        writer.close()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    server = await asyncio.start_server(handle_request, "0.0.0.0", PORT)
    logger.info(f"Datazo Mini App API listening on :{PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
