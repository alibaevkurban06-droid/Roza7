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

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN", "")

if not TOKEN:
    raise SystemExit("BOT_TOKEN не найден!")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Упрощённый антифлуд без middleware (чтобы не падать)
flood = defaultdict(list)

# Хендлеры
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Роза жива! Я вернулась навсегда\n\n/img <промпт> — картинка")

@dp.message(Command("img"))
async def img(m: types.Message):
    if not REPLICATE_TOKEN:
        await m.answer("Генерация выключена")
        return
    prompt = m.text.partition(" ")[2] or "рыжеволосая девушка с тату и кофе"
    msg = await m.answer("Генерирую…")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.replicate.com/v1/predictions", headers={"Authorization": f"Token {REPLICATE_TOKEN}"}, json={
                "version": "c221b2b8ef527988fb59bf24a8b97c0329f37ff2f90d4d2cfe46bd29d30f86d9",
                "input": {"prompt": prompt}
            }) as r:
                data = await r.json()
            pid = data["id"]
            while True:
                await asyncio.sleep(3)
                async with s.get(f"https://api.replicate.com/v1/predictions/{pid}", headers={"Authorization": f"Token {REPLICATE_TOKEN}"}) as r:
                    res = await r.json()
                if res["status"] == "succeeded":
                    await msg.delete()
                    await m.answer_photo(res["output"][0], caption=prompt)
                    break
                if res["status"] in ["failed", "canceled"]:
                    await msg.edit_text("Ошибка")
                    break
    except Exception as e:
        logging.error(e)
        await msg.edit_text("Что-то сломалось")

@dp.message(lambda m: m.text and ("роза" in m.text.lower() or "roza" in m.text.lower()))
async def call(m: types.Message):
    await m.reply("Роза Да, мой?")

@dp.message(lambda m: m.text and any(w in m.text.lower() for w in ["сука","блять","пидр","хуй"]))
async def mat(m: types.Message):
    await m.reply("Сам такой")

@dp.message()
async def echo(m: types.Message):
    # Антифлуд здесь
    uid = m.from_user.id
    now = asyncio.get_event_loop().time()
    flood[uid] = [t for t in flood[uid] if now - t < 2]
    if len(flood[uid]) >= 4:
        await m.reply("Не спамь")
        return
    flood[uid].append(now)
    await m.reply("Чё надо?")

# Webhook хэндлер
async def webhook_handler(request):
    try:
        update = Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        logging.error(e)
        return web.Response(status=500, text="Error")

app = web.Application()
app.router.add_post("/webhook", webhook_handler)

# Запуск
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
