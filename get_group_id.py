import os
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message()
async def get_group_id(message: types.Message):
    chat_id = message.chat.id
    await message.reply(f"ID этой группы: {chat_id}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
