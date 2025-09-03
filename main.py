import os
import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

# Токен бота
TOKEN = os.getenv("BOT_TOKEN")

# ID группы, куда бот будет отправлять заявки
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # Убедимся, что ID - это число

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# Определение состояний для пошагового ввода данных
class OrderForm(StatesGroup):
    name = State()
    contact = State()
    product = State()
    extra = State()


# Хранилище данных пользователей (имя, телефон)
user_data = {}


@dp.message(F.text == "/start")
async def start_order(message: types.Message, state: FSMContext):
    await message.reply(
        "👋 Добро пожаловать!\n\n"
        "🛍 **Каталог товаров:** [Открыть каталог](https://a.wsxc.cn/ItS5XIV)\n\n"
        "📌 Для оформления заявки следуйте инструкциям."
    )
    await state.set_state(OrderForm.name)
    await message.reply("👤 Введите ваше имя и фамилию:")


@dp.message(OrderForm.name)
async def get_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    
    # Проверяем, что имя содержит минимум 2 слова (имя и фамилия)
    if len(name.split()) < 2:
        await message.reply(
            "❌ Пожалуйста, введите полное имя и фамилию (минимум 2 слова).\n"
            "Например: Иван Иванов"
        )
        return
    
    # Проверяем, что имя не слишком короткое
    if len(name) < 5:
        await message.reply("❌ Имя слишком короткое. Пожалуйста, введите полное имя и фамилию.")
        return
    
    await state.update_data(name=name)
    await state.set_state(OrderForm.contact)
    await message.reply("📞 Введите ваш номер Telegram или WhatsApp (начиная с + и кода страны):")


@dp.message(OrderForm.contact)
async def get_contact(message: types.Message, state: FSMContext):
    contact = message.text.strip()
    
    # Проверяем формат номера телефона
    # Принимаем форматы: +7xxxxxxxxxx, 8xxxxxxxxxx, или @username
    phone_pattern = r'^(\+\d{10,15}|8\d{10}|@[a-zA-Z0-9_]{5,})$'
    
    # Убираем пробелы, дефисы и скобки для проверки
    cleaned_contact = re.sub(r'[\s\-\(\)]', '', contact)
    
    if not cleaned_contact:
        await message.reply("❌ Номер телефона не может быть пустым. Пожалуйста, введите номер.")
        return
    
    # Проверяем, что это либо номер телефона, либо username
    if not (cleaned_contact.startswith('+') or cleaned_contact.startswith('8') or cleaned_contact.startswith('@')):
        await message.reply(
            "❌ Неверный формат. Введите номер телефона с кодом страны (+7...) "
            "или ваш Telegram username (@username)"
        )
        return
    
    # Минимальная длина для номера телефона
    if cleaned_contact.startswith(('+', '8')) and len(cleaned_contact) < 11:
        await message.reply("❌ Номер телефона слишком короткий. Введите полный номер с кодом страны.")
        return
    
    await state.update_data(contact=contact)
    await state.set_state(OrderForm.product)
    await message.reply("📌 Отправьте ссылку на товар или прикрепите скриншот:")


@dp.message(OrderForm.product, F.text | F.photo)
async def get_product(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    
    # Получаем username пользователя
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
    
    user_data[user_id] = {
        "name": data["name"], 
        "contact": data["contact"],
        "username": username
    }

    if message.photo:
        # Сохраняем file_id фото (берем фото с лучшим качеством - последнее в массиве)
        photo_file_id = message.photo[-1].file_id
        await state.update_data(product="[Фото товара]", photo_file_id=photo_file_id)
    else:
        # Если это текст (ссылка на товар)
        await state.update_data(product=message.text, photo_file_id=None)
    
    await state.set_state(OrderForm.extra)
    await message.reply(
        "✏️ Напишите дополнительные вопросы (если есть) или отправьте '/skip' для завершения:"
    )


@dp.message(OrderForm.extra)
async def get_extra(message: types.Message, state: FSMContext):
    extra_text = (
        message.text
        if message.text.lower() != "/skip"
        else "Без дополнительных вопросов"
    )
    data = await state.get_data()

    # Получаем username из сохраненных данных пользователя
    user_id = message.from_user.id
    username = user_data.get(user_id, {}).get('username', f"ID: {user_id}")
    
    order_text = (
        f"<b>Новая заявка:</b>\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Telegram:</b> {username}\n"
        f"📞 <b>Контакт:</b> {data['contact']}\n"
        f"📌 <b>Товар:</b> {data['product']}\n"
        f"✏️ <b>Доп. инфо:</b> {extra_text}"
    )

    # Если есть фото, отправляем его с подписью, иначе отправляем только текст
    if data.get('photo_file_id'):
        await bot.send_photo(
            GROUP_CHAT_ID, 
            photo=data['photo_file_id'], 
            caption=order_text, 
            parse_mode=ParseMode.HTML
        )
    else:
        await bot.send_message(GROUP_CHAT_ID, order_text, parse_mode=ParseMode.HTML)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сделать повторную заявку", callback_data="repeat_order"
                )
            ]
        ]
    )

    await message.reply("✅ Ваша заявка обрабатывается!", reply_markup=keyboard)
    await state.clear()


@dp.callback_query(F.data == "repeat_order")
async def repeat_order(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    # Проверяем, есть ли сохраненные данные пользователя
    if user_id in user_data:
        # Восстанавливаем имя и контакт из предыдущей заявки
        await state.update_data(
            name=user_data[user_id]["name"],
            contact=user_data[user_id]["contact"]
        )
        await state.set_state(OrderForm.product)
        await bot.send_message(
            callback_query.from_user.id,
            f"✅ Используем ваши данные из предыдущей заявки:\n"
            f"👤 {user_data[user_id]['name']}\n"
            f"📞 {user_data[user_id]['contact']}\n\n"
            f"📌 Отправьте ссылку на товар или прикрепите скриншот:",
        )
    else:
        # Если данных нет, начинаем заново
        await state.set_state(OrderForm.name)
        await bot.send_message(
            callback_query.from_user.id,
            "👤 Введите ваше имя и фамилию:",
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
