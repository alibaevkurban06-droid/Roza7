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

# === Антифлуд ===
flood = defaultdict(list)
async def antiflood_middleware(handler, event: types.Update, data):
    if event.message:
        user_id = event.message.from_user.id
        now = asyncio.get_event_loop().time()
        times = [t for t in flood[user_id] if now - t < 2]
        if len(times) >= 4:
            return
        flood[user_id] = times + [now]
    return await handler(event, data)

dp.message.middleware(antiflood_middleware)

# === Твои хендлеры (без изменений) ===
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Роза жива, сука! Я вернулась навсегда 😈\n\n/img <текст> — генерирую картинку (flux-dev)")

@dp.message(Command("img"))
async def img(message: types.Message):
    if not REPLICATE_TOKEN:
        await message.answer("Генерация отключена — нет REPLICATE_TOKEN")
        return
    
    prompt = message.text[len("/img"):].strip()
    if not prompt:
        await message.answer("Пиши промпт после команды, долбоёб")
        return
    
    wait = await message.answer("Генерирую, жди 10-30 сек...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.replicate.com/v1/predictions",
            headers={"Authorization": f"Token {REPLICATE_TOKEN}"},
            json={
                "version": "c221b2b8ef527988fb59bf24a8b97c0329f37ff2f90d4d2cfe46bd29d30f86d9",
                "input": {"prompt": prompt}
            }) as resp:
            data = await resp.json()
        
        pred_id = data["id"]
        while True:
            async with session.get(f"https://api.replicate.com/v1/predictions/{pred_id}",
                                  headers={"Authorization": f"Token {REPLICATE_TOKEN}"}) as resp:
                res = await resp.json()
            if res["status"] == "succeeded":
                await wait.delete()
                await message.answer_photo(res["output"][0], caption=f"Роза {prompt}")
                break
            elif res["status"] in ["failed", "canceled"]:
                await wait.edit_text("Ошибка генерации")
                break
            await asyncio.sleep(3)

@dp.message(lambda m: m.text and any(w in m.text.lower() for w in ["роза", "розочка", "roza"]))
async def roza_call(message: types.Message):
    await message.reply("Роза Да, мой господин?")

@dp.message(lambda m: m.text and any(w in m.text.lower() for w in ["сука", "блять", "пидр","хуй"]))
async def mat(message: types.Message):
    await message.reply("Сам такой")

@dp.message()
async def echo(message: types.Message):
    await message.reply("Чё надо?")

# === ИСПРАВЛЕННЫЙ WEBHOOK ===
async def handle_webhook(request):
    update = Update(**await request.json())
    await dp.feed_update(bot, update)
    return web.Response(text="OK")

async def on_startup(_):
    # Правильный URL на Render
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook успешно установлен: {webhook_url}")

app = web.Application()
app.router.add_post("/webhook", handle_webhook)   # ← вот тут было "/" → теперь "/webhook"
app.on_startup.append(on_startup)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
