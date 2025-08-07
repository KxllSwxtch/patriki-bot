import os
import logging
import asyncio
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
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.contact)
    await message.reply("📞 Введите ваш номер Telegram или WhatsApp:")


@dp.message(OrderForm.contact)
async def get_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(OrderForm.product)
    await message.reply("📌 Отправьте ссылку на товар или прикрепите скриншот:")


@dp.message(OrderForm.product, F.text | F.photo)
async def get_product(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    user_data[user_id] = {"name": data["name"], "contact": data["contact"]}

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

    order_text = (
        f"<b>Новая заявка:</b>\n"
        f"👤 {data['name']}\n"
        f"📞 {data['contact']}\n"
        f"📌 {data['product']}\n"
        f"✏️ {extra_text}"
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
    await state.set_state(OrderForm.product)
    await bot.send_message(
        callback_query.from_user.id,
        "📌 Отправьте ссылку на товар или прикрепите скриншот:",
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
