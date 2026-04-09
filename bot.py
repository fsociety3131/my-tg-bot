import os
import sqlite3
import uuid
from datetime import datetime, timedelta
import asyncio
import hashlib
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = "http://avend.fun/api/index.php"
API_KEY = "avend_secret_2024_x9k2m4n6p8q0"

PRICE_STARS = 200
PRODUCT_NAME = "AvendDLC Minecraft"
PRODUCT_DESCRIPTION = "Чит для Minecraft 1.21.8 | Навсегда"

LOADER_URL = "https://avend.fun/loader.exe"

# ============================================
# HTTP ЗАПРОСЫ К API
# ============================================

async def api_request(method: str, data: dict = None):
    async with aiohttp.ClientSession() as session:
        headers = {
            'Content-Type': 'application/json',
            'X-Auth-Token': API_KEY
        }
        params = {'method': method}
        async with session.post(API_URL, params=params, json=data or {}, headers=headers) as resp:
            return await resp.json()

# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class AuthState(StatesGroup):
    waiting_login = State()
    waiting_register = State()

# ============================================
# БОТ
# ============================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await api_request('check_subscription', {'telegram_id': message.from_user.id})
    
    if user.get('success') and user.get('subscription_status') == 'active':
        await message.answer(
            f"👋 С возвращением!\n"
            f"📅 Статус: ✅ Активна\n"
            f"⏱️ Действует до: {user.get('subscription_end', 'Не указано')}\n"
            f"🔑 Ключ: <code>{user.get('license_key', 'Нет')}</code>",
            parse_mode="HTML",
            reply_markup=after_login_keyboard()
        )
    else:
        await message.answer(
            "🎮 <b>AvendDLC Minecraft</b>\n\n"
            "🔥 Чит для Minecraft 1.21.8\n\n"
            "👇 Войди или зарегистрируйся:",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Вход", callback_data="login")],
        [InlineKeyboardButton(text="📝 Регистрация", callback_data="register")],
        [InlineKeyboardButton(text="📥 Скачать лоадер", callback_data="download")]
    ])

def after_login_keyboard(is_admin=False):
    kb = [
        [InlineKeyboardButton(text="💎 Купить подписку (200⭐)", callback_data="buy")],
        [InlineKeyboardButton(text="📥 Скачать лоадер", callback_data="download")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ]
    if is_admin:
        kb.append([InlineKeyboardButton(text="👑 Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ============================================
# ОБРАБОТЧИКИ ВХОДА/РЕГИСТРАЦИИ
# ============================================

@dp.callback_query_handler(lambda c: c.data == "login")
async def login_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔑 Введите логин и пароль в формате:\n`логин:пароль`")
    await state.set_state(AuthState.waiting_login)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "register")
async def register_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите логин и пароль в формате:\n`логин:пароль`")
    await state.set_state(AuthState.waiting_register)
    await callback.answer()

@dp.message(AuthState.waiting_login)
async def process_login(message: types.Message, state: FSMContext):
    try:
        login, password = message.text.split(":", 1)
        result = await api_request('login', {
            'login': login,
            'password': password,
            'telegram_id': message.from_user.id
        })
        
        if result.get('success'):
            user = result['user']
            await message.answer(
                f"✅ Добро пожаловать, {login}!\n"
                f"📅 Статус: {'✅ Активна' if user['subscription_status'] == 'active' else '❌ Не активна'}\n"
                f"⏱️ Действует до: {user['subscription_end'] or 'Не куплена'}",
                reply_markup=after_login_keyboard(is_admin=user.get('is_admin', 0) == 1)
            )
        else:
            await message.answer("❌ Неверный логин или пароль")
        await state.clear()
    except:
        await message.answer("❌ Неверный формат. Используйте: `логин:пароль`")

@dp.message(AuthState.waiting_register)
async def process_register(message: types.Message, state: FSMContext):
    try:
        login, password = message.text.split(":", 1)
        result = await api_request('register', {
            'login': login,
            'password': password,
            'telegram_id': message.from_user.id
        })
        
        if result.get('success'):
            await message.answer(f"✅ Регистрация прошла успешно!\nДобро пожаловать, {login}!", reply_markup=after_login_keyboard())
        else:
            await message.answer(f"❌ {result.get('error', 'Ошибка регистрации')}")
        await state.clear()
    except:
        await message.answer("❌ Неверный формат. Используйте: `логин:пароль`")

@dp.callback_query_handler(lambda c: c.data == "logout")
async def logout(callback: types.CallbackQuery):
    await callback.message.answer("🚪 Вы вышли. Для входа нажмите /start", reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "download")
async def download_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        f"📥 <b>Скачай лоадер:</b>\n\n{LOADER_URL}\n\n"
        "1. Запустите от администратора\n"
        "2. Введите лицензионный ключ\n"
        "3. Нажмите Inject\n"
        "4. Запустите Minecraft 1.21.8",
        parse_mode="HTML"
    )
    await callback.answer()

# ============================================
# ЗАПУСК
# ============================================

async def main():
    print("🤖 AvendDLC бот запущен!")
    print("✅ API подключён к https://avend.fun/api/")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
