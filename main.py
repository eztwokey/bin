import os
import base64
import json
import logging
from io import BytesIO
from typing import Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from PIL import Image

from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not OPENAI_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise SystemExit("Please set OPENAI_API_KEY and TELEGRAM_BOT_TOKEN in .env")

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Telegram bot
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Load system prompt
with open(os.path.join(os.path.dirname(__file__), "prompt_system.txt"), "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

HELP_TEXT = (
    "<b>RSI+MACD Vision Bot</b>\n\n"
    "Отправьте скриншот графика (M5) с RSI(14) и MACD(12,26,9), и бот вернет прогноз на 30 минут.\n\n"
    "<b>Советы по скрину:</b>\n"
    "- Видны последние 6–12 свечей\n"
    "- RSI с уровнями 30/70\n"
    "- MACD с нулевой линией, MACD и Signal видны\n"
    "- Название пары по возможности\n"
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(HELP_TEXT)

@dp.message(F.photo | F.document)
async def handle_image(message: Message):
    # Accept photo or image document
    try:
        if message.photo:
            # Take highest resolution photo
            file = await bot.get_file(message.photo[-1].file_id)
        else:
            # document (ensure it's image/*)
            if not message.document or not message.document.mime_type or not message.document.mime_type.startswith("image/"):
                await message.reply("Пожалуйста, пришлите изображение (скриншот графика).")
                return
            file = await bot.get_file(message.document.file_id)

        file_path = file.file_path
        file_bytes = await bot.download_file(file_path)

        img = Image.open(file_bytes).convert("RGB")
        # Compress to reasonable quality to control token costs
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64}"

        user_instruction = (
            "Analyze this chart screenshot using the given strategy. "
            "Return ONLY the required JSON. Use careful visual reading."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_instruction},
                    {"type": "input_image", "image_url": {"url": data_url}}
                ],
            },
        ]

        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content.strip()

        try:
            parsed: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON substring
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(raw[start:end+1])
            else:
                await message.reply("Не удалось распарсить ответ модели. Попробуйте переснять скрин четче.")
                return

        # Validate minimal keys
        required_keys = {"direction", "confidence", "horizon_minutes"}
        if not required_keys.issubset(set(parsed.keys())):
            await message.reply(f"Ответ неполный: {parsed}")
            return

        direction = parsed.get("direction", "UNCERTAIN")
        confidence = parsed.get("confidence", 0)
        horizon = parsed.get("horizon_minutes", 30)
        pair = parsed.get("pair", "UNKNOWN")
        rationale = parsed.get("rationale", "")
        checks = parsed.get("checks", {})

        text = (
            f"<b>Пара:</b> {pair}\n"
            f"<b>Прогноз (30 мин):</b> {('⬆️ UP' if direction=='UP' else '⬇️ DOWN' if direction=='DOWN' else '⚪ UNCERTAIN')}\n"
            f"<b>Уверенность:</b> {confidence}%\n"
            f"<b>Обоснование:</b> {rationale}\n\n"
            f"<b>Проверки:</b>\n"
            f"• MACD zero bias: {checks.get('macd_zero_bias', 'UNKNOWN')}\n"
            f"• MACD vs Signal: {checks.get('macd_signal_relation', 'UNKNOWN')}\n"
            f"• RSI: {checks.get('rsi_state', 'UNKNOWN')}\n"
            f"• Price structure: {checks.get('price_structure', 'UNKNOWN')}\n"
            f"• Screenshot: {checks.get('screenshot_quality', 'UNKNOWN')}"
        )
        await message.reply(text)
    except Exception as e:
        logging.exception("Error processing image")
        await message.reply(f"Ошибка обработки: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
