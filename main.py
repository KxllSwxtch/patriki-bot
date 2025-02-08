import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

# Токен бота
TOKEN = os.getenv("BOT_TOKEN")

# ID группы, куда бот будет отправлять заявки
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # Убедимся, что ID - это число

# ID администратора (клиент и его напарник)
ADMIN_IDS = {123456789, 987654321}  # Заменить на реальные Telegram ID

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


@dp.message()
async def handle_message(message: types.Message):
    if message.text and message.text.startswith("/start"):
        await message.reply(
            "Привет! 👋 Добро пожаловать!\n\n"
            "📌 Для оформления заявки отправьте:\n"
            "- Фото товара или ссылку на него\n"
            "- Ваше имя\n"
            "- Ваш номер телефона или Telegram\n\n"
            "📷 Вы также можете прикрепить фото к заявке!\n\n"
            "🛍 **Каталог товаров:** [Открыть каталог](https://a.wsxc.cn/ItS5XIV)"
        )
    elif (
        message.text
        and message.text.startswith("/заявки")
        and message.from_user.id in ADMIN_IDS
    ):
        await message.reply("Сохранение заявок в базе данных временно отключено.")
    elif message.text or message.photo:
        order_text = message.caption if message.caption else message.text
        photo_id = message.photo[-1].file_id if message.photo else None

        if not (
            order_text
            and any(x in order_text.lower() for x in ["имя", "телефон", "@", "tg"])
        ):
            await message.reply(
                "Формат заявки неверный!\n\nПример:\n"
                "https://example.com/product\n"
                "Имя: Иван Иванов\n"
                "Телефон/Telegram: @ivanivanov\n\n"
                "🛍 **Каталог товаров:** [Открыть каталог](https://a.wsxc.cn/ItS5XIV)"
            )
            return

        order_text = f"<b>Новая заявка:</b>\n{order_text}\n"

        if photo_id:
            await bot.send_photo(
                GROUP_CHAT_ID, photo_id, caption=order_text, parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(GROUP_CHAT_ID, order_text, parse_mode=ParseMode.HTML)

        await message.reply(
            "✅ Ваша заявка обрабатывается!\n\n"
            "Вы можете продолжить выбирать товары в каталоге: https://a.wsxc.cn/ItS5XIV",
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
