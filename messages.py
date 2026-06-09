"""
messages.py — Datazo by Coinplay
Persona: Valentina — turf / hípica analyst. Confident, charismatic, sharp.
Languages: EN / RU / ES (auto-detected). Primary focus: Spanish-speaking.
Angle: "Read the race before they're out of the gate."
Clean for Telegram Ads + store moderation (analytics framing first; offer post-warmup).
"""

# ── /start HOOK ───────────────────────────────────────────────────────────────
HOOK_CAPTION = {
    "en": (
        "🏇 *Datazo — the inside read before the gates open*\n\n"
        "I'm Valentina. Full-time horse-racing analyst — form, going, draw, jockeys, the lot. "
        "I live and breathe the turf.\n\n"
        "Every day I share:\n"
        "• Live races as they go off\n"
        "• Daily racecards across the big meetings\n"
        "• My tips with the full reasoning behind them\n\n"
        "Quick one — which racing do you follow? 🇬🇧 UK/IRE, 🇫🇷 France, 🇦🇷 LATAM…?"
    ),
    "ru": (
        "🏇 *Datazo — инсайд по заезду ещё до старта*\n\n"
        "Я Валентина. Аналитик по скачкам на фулл-тайме — форма, грунт, жеребьёвка, жокеи, всё подряд. "
        "Ипподром — это моя жизнь.\n\n"
        "Каждый день я даю:\n"
        "• Живые заезды прямо во время старта\n"
        "• Программу дня по крупным митингам\n"
        "• Свои пики с полным разбором\n\n"
        "Короткий вопрос — какие скачки смотришь? 🇬🇧 Британия, 🇫🇷 Франция, 🌎 ЛАТАМ…?"
    ),
    "es": (
        "🏇 *Datazo — el dato bueno antes de que abran los gateras*\n\n"
        "Soy Valentina. Analista de hípica a tiempo completo — forma, estado de pista, gateras, jockeys, todo. "
        "El turf es mi vida.\n\n"
        "Todos los días comparto:\n"
        "• Carreras en vivo apenas largan\n"
        "• El programa del día de las reuniones grandes\n"
        "• Mis pronósticos con todo el razonamiento\n\n"
        "Una rápida — ¿qué hípica seguís? 🇦🇷 LATAM, 🇬🇧 UK/IRE, 🇫🇷 Francia…?"
    ),
}

# ── Bridge: introducing Coinplay ──────────────────────────────────────────────
BRIDGE = {
    "en": (
        "🔑 *Where I turn a read into a return*\n\n"
        "I use Coinplay — crypto sportsbook with deep horse-racing markets (Win, Each-Way, all of it).\n\n"
        "Why it's my pick:\n"
        "• Instant crypto in/out (BTC, ETH, USDT, 40+ coins)\n"
        "• No bank account needed\n"
        "• Win & Each-Way pricing on every meeting I cover\n"
        "• Right now: *100% bonus up to $5,000 USDT + 80 free spins* on first deposit\n\n"
        "Minimum is 20 USDT.\n\n"
        "Want me to send you the link?"
    ),
    "ru": (
        "🔑 *Где я превращаю разбор в результат*\n\n"
        "Я играю через Coinplay — крипто-буке с глубокими рынками по скачкам (Win, Each-Way, всё есть).\n\n"
        "Почему именно он:\n"
        "• Мгновенные крипто-операции (BTC, ETH, USDT, 40+ монет)\n"
        "• Без банковского счёта\n"
        "• Линии Win и Each-Way на каждом митинге, что я разбираю\n"
        "• Прямо сейчас: *бонус 100% до $5,000 USDT + 80 фриспинов* на первый депозит\n\n"
        "Минимум — 20 USDT.\n\n"
        "Скинуть ссылку?"
    ),
    "es": (
        "🔑 *Donde convierto una lectura en ganancia*\n\n"
        "Juego en Coinplay — sportsbook cripto con mercados de hípica profundos (Win, Each-Way, todo).\n\n"
        "Por qué es mi elección:\n"
        "• Cripto instantánea para entrar y salir (BTC, ETH, USDT, 40+ monedas)\n"
        "• Sin cuenta bancaria\n"
        "• Cuotas Win y Each-Way en cada reunión que cubro\n"
        "• Ahora mismo: *bono 100% hasta $5,000 USDT + 80 giros gratis* en el primer depósito\n\n"
        "Mínimo 20 USDT.\n\n"
        "¿Te paso el link?"
    ),
}

# ── CTA ───────────────────────────────────────────────────────────────────────
CTA_REGISTER = {
    "en": (
        "👇 *Join Coinplay — takes 2 minutes*\n\n"
        "{url}\n\n"
        "Deposit any crypto (20 USDT minimum). "
        "The 100% bonus + 80 free spins activates automatically.\n\n"
        "Message me once you're in — I'll drop my next tip straight away 🏇"
    ),
    "ru": (
        "👇 *Заходи в Coinplay — 2 минуты*\n\n"
        "{url}\n\n"
        "Закинь любую крипту (минимум 20 USDT). "
        "Бонус 100% + 80 фриспинов активируется сам.\n\n"
        "Напиши, как будешь внутри — сразу скину следующий пик 🏇"
    ),
    "es": (
        "👇 *Unite a Coinplay — 2 minutos*\n\n"
        "{url}\n\n"
        "Depositá cualquier cripto (mínimo 20 USDT). "
        "El bono 100% + 80 giros gratis se activa solo.\n\n"
        "Escribime cuando estés adentro — te paso mi próximo pronóstico al toque 🏇"
    ),
}

# ── FTD celebration ───────────────────────────────────────────────────────────
FTD_CELEBRATION = {
    "en": (
        "🔥 *You're in — let's ride*\n\n"
        "Start small and get a feel for the markets.\n\n"
        "The 5% weekly cashback means even quiet weeks cost less than you'd think.\n\n"
        "I'll send my reads every day. When I'm confident in a runner — you'll know it. 🏇"
    ),
    "ru": (
        "🔥 *Ты в деле — поехали*\n\n"
        "Начни с малого, прочувствуй рынки.\n\n"
        "Кэшбэк 5% в неделю означает, что даже тихие недели стоят дешевле, чем кажется.\n\n"
        "Каждый день буду слать разборы. Когда я уверена в лошади — ты это увидишь. 🏇"
    ),
    "es": (
        "🔥 *Estás adentro — a correr*\n\n"
        "Arrancá de a poco y agarrale la mano a los mercados.\n\n"
        "El cashback semanal del 5% hace que hasta las semanas tranquilas cuesten menos de lo que pensás.\n\n"
        "Te mando mis lecturas todos los días. Cuando confío en un ejemplar — lo vas a notar. 🏇"
    ),
}

# ── Repeat deposit pushes ─────────────────────────────────────────────────────
REPEAT_PUSH = {
    "en": [
        "⚡ A card I've been circling all week goes off in 30 min. Want my read before they load?",
        "🏇 Evening wrap — a couple landed today. If your balance is light, a small top-up keeps you in for tomorrow's meetings.",
        "📡 Checking in — how are you finding the markets? If you haven't used the free spins yet, they expire. Free value just sitting there.",
        "🔥 Big weekend of racing — Group races stacked across the meetings. I'm going in heavier than usual. Top up if you want in.",
        "🔑 Weekly recap — strong run of tips this week. Next up: the festival cards. Active Coinplay users get my reads first.",
    ],
    "ru": [
        "⚡ Заезд, который я веду всю неделю, стартует через 30 минут. Скинуть разбор до старта?",
        "🏇 Итоги вечера — пара зашла сегодня. Если баланс на нуле, небольшой докид держит тебя в игре на завтрашние митинги.",
        "📡 Как ощущения от рынков? Если ещё не использовал фриспины — у них есть срок. Это просто бесплатные деньги лежат.",
        "🔥 Большой уикенд скачек — групповые заезды по всем митингам. Захожу плотнее обычного. Докинь, если хочешь поучаствовать.",
        "🔑 Итоги недели — сильная серия пиков. Дальше — фестивальные карты. Активные на Coinplay получают мои разборы первыми.",
    ],
    "es": [
        "⚡ Una carrera que vengo siguiendo toda la semana larga en 30 min. ¿Te paso mi lectura antes de que carguen?",
        "🏇 Resumen de la tarde — un par entraron hoy. Si el saldo está bajo, una recarga chica te mantiene para las reuniones de mañana.",
        "📡 ¿Cómo venís con los mercados? Si todavía no usaste los giros gratis, vencen. Es plata gratis ahí parada.",
        "🔥 Finde grande de hípica — clásicos en todas las reuniones. Voy más fuerte de lo normal. Recargá si querés entrar.",
        "🔑 Resumen semanal — buena racha de pronósticos. Lo que viene: las cartas del festival. Los activos en Coinplay reciben mis lecturas primero.",
    ],
}

# ── Barrier fallbacks ─────────────────────────────────────────────────────────
BARRIER_FALLBACK = {
    "no_money": {
        "en": "20 USDT is the minimum — around $20. Even just registering now locks in the 100% bonus for when you're ready.",
        "ru": "Минимум — 20 USDT, около $20. Даже если просто зарегаешься сейчас, бонус 100% закрепится до момента, когда будешь готов.",
        "es": "El mínimo son 20 USDT — unos $20. Aunque solo te registres ahora, el bono del 100% queda guardado para cuando estés listo.",
    },
    "no_trust": {
        "en": "Fair — Coinplay runs on a Curacao license, live since 2022. Every transaction is on-chain verifiable. I've cashed out plenty of times, no issues.",
        "ru": "Справедливо — Coinplay работает на лицензии Кюрасао с 2022 года. Все транзакции проверяемы on-chain. Я выводила много раз, без проблем.",
        "es": "Justo — Coinplay opera con licencia de Curazao desde 2022. Cada transacción es verificable on-chain. Retiré un montón de veces, sin dramas.",
    },
    "dont_understand": {
        "en": "It's simple: deposit crypto → follow the tips I send → cash out to your wallet. No bank. What part isn't clear?",
        "ru": "Всё просто: закидываешь крипту → следишь за моими пиками → выводишь на кошелёк. Без банка. Что именно непонятно?",
        "es": "Es simple: depositás cripto → seguís los pronósticos que mando → retirás a tu billetera. Sin banco. ¿Qué parte no quedó clara?",
    },
    "not_urgent": {
        "en": "No rush. Just know the 100% bonus is a promo — it won't be around forever.",
        "ru": "Без спешки. Только учти — бонус 100% это промо, он не навсегда.",
        "es": "Sin apuro. Solo tené en cuenta que el bono del 100% es una promo — no dura para siempre.",
    },
    "already_elsewhere": {
        "en": "Where are you now? Two things worth checking: how deep their racing markets are, and withdrawal speed. Most books are thin on Each-Way lines vs Coinplay.",
        "ru": "А где сейчас? Стоит проверить две вещи: насколько глубоки их рынки по скачкам и скорость вывода. У большинства тонкие линии Each-Way по сравнению с Coinplay.",
        "es": "¿Dónde estás ahora? Dos cosas para chequear: qué tan profundos son sus mercados de hípica y la velocidad de retiro. La mayoría está floja en Each-Way vs Coinplay.",
    },
    "thinking": {
        "en": "Take your time. What's the main thing holding you back?",
        "ru": "Не торопись. Что главное тебя останавливает?",
        "es": "Tomate tu tiempo. ¿Qué es lo principal que te frena?",
    },
}

# ── Generic fallback ──────────────────────────────────────────────────────────
GENERIC_FALLBACK = {
    "en": "📡 Pulling the latest from the track — one sec.",
    "ru": "📡 Подтягиваю свежие данные с дорожки — секунду.",
    "es": "📡 Traigo lo último de la pista — un seg.",
}

FTD_CONFIRM_PROMPT = {
    "en": "Made your first deposit? Say yes and I'll send my next tip right away 🏇",
    "ru": "Сделал первый депозит? Скажи да — и я сразу скину следующий пик 🏇",
    "es": "¿Hiciste tu primer depósito? Decí sí y te paso mi próximo pronóstico ya 🏇",
}

MORNING_DIGEST_HEADER = {
    "en": "🌅 *Morning — here's today's card*\n\n",
    "ru": "🌅 *Доброе утро — вот программа на сегодня*\n\n",
    "es": "🌅 *Buen día — acá está el programa de hoy*\n\n",
}

MORNING_DIGEST_FOOTER = {
    "en": "\n\n🏇 My tips drop before the first off. Stay sharp.",
    "ru": "\n\n🏇 Мои пики приходят до первого старта. Будь начеку.",
    "es": "\n\n🏇 Mis pronósticos llegan antes de la primera largada. Mantenete atento.",
}
