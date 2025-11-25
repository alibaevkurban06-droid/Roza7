import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN", "")

bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === АНТИФЛУД ===
from collections import defaultdict
flood = defaultdict(list)

async def anti_flood(**kwargs):
    user_id = kwargs["update"].message.from_user.id
    now = asyncio.get_event_loop().time()
    times = [t for t in flood[user_id] if now - t < 2]
    if len(times) >= 4:
        return False
    flood[user_id] = times + [now]
    return True

# === ХЕНДЛЕРЫ ===
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("🌹 Роза жива, сука! Я вернулась навсегда 😈\n\n/img <текст> — генерирую картинку (flux-dev)")

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
                await message.answer_photo(res["output"][0], caption=f"🌹 {prompt}")
                break
            elif res["status"] in ["failed", "canceled"]:
                await wait.edit_text("Ошибка генерации")
                break
            await asyncio.sleep(3)

@dp.message(F.text.lower().contains(("роза", "розочка", "roza")))
async def roza_call(message: Message):
    await message.reply("🌹 Да, мой господин?")

@dp.message(F.text.lower().contains(("сука", "блять", "пидр", "хуй")))
async def mat(message: Message):
    await message.reply("Сам такой 😏")

@dp.message()
async def echo(message: Message):
    await message.reply("Чё надо?")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
