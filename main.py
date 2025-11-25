import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import aiohttp
from collections import defaultdict

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN", "")

from aiogram.client.default import DefaultBotProperties
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === АНТИФЛУД ===
flood = defaultdict(list)

async def anti_flood(**kwargs):
    user_id = kwargs["update"].message.from_user.id
    now = asyncio.get_event_loop().time()
    times = [t for t in flood[user_id] if now - t < 2]
    if len(times) >= 4:
        return False
    flood[user_id] = times + [now]
    return True

# === ТВОИ ХЕНДЛЕРЫ (без изменений) ===
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Роза жива, сука! Я вернулась навсегда 😈\n\n/img <текст> — генерирую картинку (flux-dev)")

@dp.message(Command("img"))
async def img(message: Message):
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

@dp.message(F.text.lower().contains(("роза", "розочка", "roza")))
async def roza_call(message: Message):
    await message.reply("Роза Да, мой господин?")

@dp.message(F.text.lower().contains(("сука", "блять", "пидр", "хуй")))
async def mat(message: Message):
    await message.reply("Сам такой 😏")

@dp.message()
async def echo(message: Message):
    await message.reply("Чё надо?")

# === WEBHOOK ЧАСТЬ (это то, что заставит работать на Render) ===
async def handle_webhook(request):
    update = Update(**await request.json())
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup(app):
    webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}{os.environ.get('RENDER_EXTERNAL_URL', '/')}"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook установлен: {webhook_url}")

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post("/", handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# Запуск через gunicorn (Render сам использует его)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
