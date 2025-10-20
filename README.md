# RSI+MACD Vision Telegram Bot

A Telegram bot that accepts **your screenshots** of charts (with RSI and MACD shown), sends them to an LMM with vision,
and returns a **30‑minute direction forecast (↑/↓)** plus a confidence score using the defined **Trend+Pullback Strategy**.

---

## What the bot does
1. You send a screenshot of a chart (timeframe **M5**; indicators **RSI(14)** with levels 30/70 and **MACD(12,26,9)** visible).
2. The bot forwards the image and a strict analysis prompt to the model.
3. The model returns a JSON with:
   - `direction` = "UP" / "DOWN"
   - `horizon_minutes` = 30
   - `confidence` = 0..100 (probability-like score)
   - `rationale` = short explanation
   - `checks` = extracted visual cues (RSI state, MACD alignment, trend, pullback)
4. The bot parses the JSON and replies in readable text.

> Note: The bot works **only on your images**. It does not fetch data or call exchanges.

---

## Requirements
- Python 3.10+
- A Telegram bot token from **@BotFather**
- An OpenAI API key

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file (copy from `.env.example`) and fill in:
```
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=123456:ABC...
```

Run the bot (long polling):
```bash
python main.py
```

---

## How to prepare screenshots (important)
Please include all of the following in the screenshot:
- Timeframe **M5** (5-minute candles)
- At least **30–60 last minutes** visible (6–12 candles)
- RSI(14) with levels **30/70**
- MACD with parameters **12, 26, 9**
- Asset name visible (e.g., AUD/JPY)
- Price axis and indicator scales visible

**Optional:** If you can overlay/annotate EMA50, include it. If not — the strategy uses MACD zero-line as the trend proxy.

---

## Strategy rules (summarized)
- Trend via **MACD zero-line** and price action:
  - Above zero → bias UP; below zero → bias DOWN
- Entry logic (pullback with confirmation):
  - For **UP** forecasts: prefer MACD > 0 and RSI exiting from <30 upward, or mild pullback while still aligned UP
  - For **DOWN** forecasts: prefer MACD < 0 and RSI exiting from >70 downward, or mild pullback while still aligned DOWN
- Ignore counter-trend signals unless there is strong multi-factor evidence

The model receives these rules and must output a structured JSON. The bot enforces/validates that JSON shape.

---

## Files
- `main.py` — Telegram bot (aiogram 3.x), OpenAI Vision call, JSON parsing
- `prompt_system.txt` — Strategy/system prompt for vision analysis
- `requirements.txt` — Dependencies
- `.env.example` — Example env vars
- `README.md` — You are here

---

## Deploy notes
- You can run the bot on your own PC (must stay online) or on a VPS.
- Long polling is simplest; no webhooks required.
- To keep it 24/7 on a server, use `tmux`, `screen`, or a process manager (e.g., `systemd`, `pm2` with `python`).
