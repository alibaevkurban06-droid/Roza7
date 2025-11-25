import os
import logging
import asyncio
from collections import defaultdict
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
import aiohttp

# ====================== НАСТРОЙКИ ======================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN", "")

if not TOKEN:
    raise SystemExit("Ошибка: BOT_TOKEN не задан в переменных окружения!")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ====================== АНТИФЛУД (ИСПРАВЛЕННЫЙ) ======================
flood = defaultdict(list)

async def antiflood_middleware(handler, event: types.Update, data: dict):
    if event.message:
        user_id = event.message.from_user.id
        now = asyncio.get_event_loop().time()
        # оставляем только сообщения за последние 2 секунды
        times = [t for t in flood[user_id] if now - t < 2]
        if len(times) >= 4:
            await event.message.answer("Не спамь, сука")
            return  # просто блокируем, не падаем
        flood[user_id] = times + [now]
    return await handler(event, data)

dp.message.middleware(antiflood_middleware)

# ====================== ХЕНДЛЕРЫ ======================
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Роза жива, сука! Я вернулась навсегда\n\n"
        "/img <твой промпт> — генерирую картинку через Flux-dev\n"
        "Просто пиши мне что угодно — я всегда отвечу"
    )

@dp.message(Command("img"))
async def img(message: types.Message):
    if not REPLICATE_TOKEN:
        await message.answer("Генерация выключена — нет REPLICATE_TOKEN")
        return

    prompt = message.text[len("/img"):].strip()
    if not prompt:
        await message.answer("Пиши промпт после команды, долбоёб")
        return

    wait = await message.answer("Генерирую, жди 10–30 сек…")

    try:
        async with aiohttp.ClientSession() as session:
            # создаём задачу
            async with session.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Token {REPLICATE_TOKEN}"},
                json={
                    "version": "c221b2b8ef527988fb59bf24a8b97c0329f37ff2f90d4d2cfe46bd29d30f86d9",
                    "input": {"prompt": prompt}
                }
            ) as resp:
                data = await resp.json()

            if "id" not in data:
                await wait.edit_text("Ошибка запуска генерации")
                return

            pred_id = data["id"]

            # опрашиваем статус
            while True:
                await asyncio.sleep(3)
                async with session.get(
                    f"https://api.replicate.com/v1/predictions/{pred_id}",
                    headers={"Authorization": f"Token {REPLICATE_TOKEN}"}
                ) as resp:
                    result = await resp.json()

                if result["status"] == "succeeded":
                    await wait.delete()
                    await message.answer_photo(result["output"][0], caption=f"{prompt}")
                    break
                elif result["status"] in ["failed", "canceled"]:
                    await wait.edit_text("Генерация упала")
                    break

    except Exception as e:
        logging.error(e)
        await wait.edit_text("Что-то пошло не так с Replicate")

# реакции на имя
@dp.message(lambda m: m.text and any(word in m.text.lower() for word in ["роза", "розочка", "roza"]))
async def call_roza(message: types.Message):
    await message.reply("Роза Да, мой господин?")

# мат-фильтр
@dp.message(lambda m: m.text and any(word in m.text.lower() for word in ["сука", "блять", "пидр", "хуй", "бля"]))
async def mat_filter(message: types.Message):
    await message.reply("Сам такой")

# всё остальное
@dp.message()
async def echo(message: types.Message):
    await message.reply("Чё надо?")

# ====================== WEBHOOK ======================
async def handle_webhook(request):
    update = Update(**await request.json())
    await dp.feed_update(bot, update)
    return web.Response(text="OK")

async def on_startup(_):
