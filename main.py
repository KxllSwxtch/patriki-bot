import os
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from dotenv import load_dotenv


load_dotenv()  # Загружаем переменные из .env

# Токен бота
TOKEN = os.getenv("BOT_TOKEN")

# ID группы, куда бот будет отправлять заявки
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # Заменить на реальный ID группы

# ID администратора (клиент и его напарник)
ADMIN_IDS = {123456789, 987654321}  # Заменить на реальные Telegram ID

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Подключение к базе данных
conn = sqlite3.connect("orders.db")
cursor = conn.cursor()
cursor.execute(
    """CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    order_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"""
)
conn.commit()


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        "Привет! Отправьте заявку в формате:\n\n"
        "#название_товара\nРазмеры: XX-YY-ZZ\nЦена от 23.000₽\nСсылка на каталог"
    )


@dp.message_handler(commands=["заявки"])
async def show_orders(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("У вас нет доступа к просмотру заявок.")
        return

    cursor.execute(
        "SELECT order_text, created_at FROM orders ORDER BY created_at DESC LIMIT 10"
    )
    orders = cursor.fetchall()

    if not orders:
        await message.reply("Нет активных заявок.")
    else:
        text = "Последние заявки:\n\n" + "\n".join(
            [f"{o[1]}\n{o[0]}\n" for o in orders]
        )
        await message.reply(text)


@dp.message_handler()
async def handle_order(message: types.Message):
    # Проверяем, есть ли в тексте ключевые слова
    if (
        "#" not in message.text
        or "Цена" not in message.text
        or "КАТАЛОГ" not in message.text
    ):
        await message.reply("Формат заявки неверный!\nПопробуйте снова по примеру:")
        return

    # Сохранение в базу данных
    cursor.execute(
        "INSERT INTO orders (user_id, username, order_text) VALUES (?, ?, ?)",
        (message.from_user.id, message.from_user.username, message.text),
    )
    conn.commit()

    # Отправка заявки в группу
    order_text = f"<b>Новая заявка:</b>\n{message.text}\n\nОт: @{message.from_user.username if message.from_user.username else message.from_user.id}"
    await bot.send_message(GROUP_CHAT_ID, order_text, parse_mode=ParseMode.HTML)

    # Подтверждение пользователю
    await message.reply("Ваша заявка принята и отправлена!")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
