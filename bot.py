import os
import uuid
from datetime import datetime, timedelta
import asyncio
import aiohttp
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit(1)

API_URL = "http://avend.fun/index.php"
API_KEY = "avend_secret_2024_x9k2m4n6p8q0"

PRICE_STARS = 200
PRODUCT_NAME = "AvendDLC Minecraft"
PRODUCT_DESCRIPTION = "Чит для Minecraft 1.21.8 | Навсегда"

LOADER_URL = "https://avend.fun/loader.exe"

# ============================================
# HTTP ЗАПРОСЫ К API
# ============================================

async def api_request(method: str, data: dict = None):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'Content-Type': 'application/json',
                'X-Auth-Token': API_KEY
            }
            params = {'method': method}
            async with session.post(API_URL, params=params, json=data or {}, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"API {method} success: {result}")
                    return result
                else:
                    logger.error(f"API error: {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"API request error: {e}")
        return None

# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class AuthState(StatesGroup):
    waiting_login = State()
    waiting_register = State()

# ============================================
# КЛАВИАТУРЫ
# ============================================

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

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

# ============================================
# БОТ
# ============================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        user = await api_request('check_subscription', {'telegram_id': message.from_user.id})
        
        if user and user.get('success') and user.get('subscription_status') == 'active':
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
    except Exception as e:
        logger.error(f"Start error: {e}")
        await message.answer(
            "<b>AvendDLC</b>\n\n"
            "Чит для Minecraft 1.21.8\n\n"
            "Войди или зарегистрируйся:",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

@dp.callback_query(F.data == "login")
async def login_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔑 Введите логин и пароль в формате:\n`логин:пароль`", parse_mode="Markdown")
    await state.set_state(AuthState.waiting_login)
    await callback.answer()

@dp.callback_query(F.data == "register")
async def register_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите логин и пароль в формате:\n`логин:пароль`", parse_mode="Markdown")
    await state.set_state(AuthState.waiting_register)
    await callback.answer()

@dp.message(AuthState.waiting_login)
async def process_login(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text:
            await message.answer("❌ Неверный формат. Используйте: `логин:пароль`", parse_mode="Markdown")
            return
        
        login, password = message.text.split(":", 1)
        result = await api_request('login', {
            'login': login,
            'password': password,
            'telegram_id': message.from_user.id
        })
        
        if result and result.get('success'):
            user = result['user']
            await message.answer(
                f"✅ Добро пожаловать, {login}!\n"
                f"📅 Статус: {'✅ Активна' if user.get('subscription_status') == 'active' else '❌ Не активна'}\n"
                f"⏱️ Действует до: {user.get('subscription_end') or 'Не куплена'}",
                reply_markup=after_login_keyboard(is_admin=user.get('is_admin', 0) == 1)
            )
        else:
            await message.answer("❌ Неверный логин или пароль")
        await state.clear()
    except Exception as e:
        logger.error(f"Login error: {e}")
        await message.answer("❌ Неверный формат. Используйте: `логин:пароль`", parse_mode="Markdown")
        await state.clear()

@dp.message(AuthState.waiting_register)
async def process_register(message: types.Message, state: FSMContext):
    try:
        if ":" not in message.text:
            await message.answer("❌ Неверный формат. Используйте: `логин:пароль`", parse_mode="Markdown")
            return
        
        login, password = message.text.split(":", 1)
        result = await api_request('register', {
            'login': login,
            'password': password,
            'telegram_id': message.from_user.id
        })
        
        if result and result.get('success'):
            await message.answer(f"✅ Регистрация прошла успешно!\nДобро пожаловать, {login}!", reply_markup=after_login_keyboard())
        else:
            error_msg = result.get('error', 'Ошибка регистрации') if result else 'Ошибка соединения с API'
            await message.answer(f"❌ {error_msg}")
        await state.clear()
    except Exception as e:
        logger.error(f"Register error: {e}")
        await message.answer("❌ Неверный формат. Используйте: `логин:пароль`", parse_mode="Markdown")
        await state.clear()

@dp.callback_query(F.data == "logout")
async def logout(callback: types.CallbackQuery):
    await callback.message.answer("🚪 Вы вышли. Для входа нажмите /start", reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text("🎮 Главное меню:", reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "download")
async def download_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        f"📥 <b>Скачать лоадер:</b>\n\n{LOADER_URL}\n\n",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "buy")
async def buy_callback(callback: types.CallbackQuery):
    try:
        user = await api_request('check_subscription', {'telegram_id': callback.from_user.id})
        
        if not user or not user.get('success'):
            await callback.answer("Сначала войдите в систему!", show_alert=True)
            return
        
        if user.get('subscription_status') == 'active':
            await callback.answer("У вас уже есть активная подписка!", show_alert=True)
            return
        
        payment_id = f"PAY_{callback.from_user.id}_{int(datetime.now().timestamp())}"
        await api_request('create_payment', {
            'payment_id': payment_id,
            'user_id': callback.from_user.id,
            'amount': PRICE_STARS
        })
        
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=PRODUCT_NAME,
            description=PRODUCT_DESCRIPTION,
            payload=payment_id,
            currency="XTR",
            prices=[LabeledPrice(label=PRODUCT_NAME, amount=PRICE_STARS)],
            start_parameter="avenddlc_payment",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Buy error: {e}")
        await callback.answer("Ошибка при покупке", show_alert=True)

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    if pre_checkout_q.invoice_payload.startswith("PAY_"):
        await pre_checkout_q.answer(ok=True)
        await api_request('confirm_payment', {'payment_id': pre_checkout_q.invoice_payload})
        logger.info(f"✅ Платёж принят: {pre_checkout_q.invoice_payload}")
    else:
        await pre_checkout_q.answer(ok=False, error_message="Ошибка платежа")

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    result = await api_request('confirm_payment', {'payment_id': payment.invoice_payload})
    
    if result and result.get('success'):
        license_key = result.get('license_key', '')
        await message.answer(
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"🔑 <b>Твой ключ:</b> <code>{license_key}</code>\n\n"
            f"📥 Нажми «Скачать лоадер» в главном меню",
            parse_mode="HTML",
            reply_markup=after_login_keyboard()
        )

# ============================================
# АДМИН ПАНЕЛЬ
# ============================================

@dp.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👑 <b>Админ панель</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    await callback.message.edit_text("📊 Список пользователей:\n(функция в разработке)", reply_markup=admin_keyboard())
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
