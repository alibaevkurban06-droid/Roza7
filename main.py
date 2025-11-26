import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
 raise Exception("BOT_TOKEN не задан!")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
 await message.answer("Роза жива, милый 🔥\nПиши что угодно — я отвечу.")

@dp.message()
async def echo(message: types.Message):
 text = message.text.lower()
 if any(word in text for word in ["роза", "roza"]):
 await message.reply("Роза Да, мой?")
 elif any(word in text for word in ["сука", "блять", "пидр", "хуй"]):
 await message.reply("Сам такой 😏")
 else:
 await message.reply("Чё надо?")

async def webhook(request):
 update = Update(**await request.json())
 await dp.feed_update(bot, update)
 return web.Response(text="OK")

app = web.Application()
app.router.add_post("/webhook", webhook)

if __name__ == "__main__":
 port = int(os.environ.get("PORT", 10000))
 logging.info("Бот запущен, webhook ждёт на /webhook")
 web.run_app(app, host="0.0.0.0", port=port)
