import os
import sqlite3
import uuid
from datetime import datetime, timedelta
import asyncio
import hashlib

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit(1)

DB_PATH = "avenddlc.db"
LOADER_PATH = "loader.exe"

PRICE_STARS = 200
PRODUCT_NAME = "AvendDLC Minecraft"
PRODUCT_DESCRIPTION = "Чит для Minecraft 1.21.8 | Навсегда"

# Админ (создастся при старте)
ADMIN_LOGIN = "Avend3982189321983"
ADMIN_PASSWORD = "21983821998491203092348912980xxzxxxsdasdasfjuwo23810djkJJJJJ"

# Дополнительные аккаунты (создадутся при старте)
EXTRA_ACCOUNTS = [
    {"login": "Ffacf590", "password": "mark12345678mark"},
    {"login": "kw2zuk", "password": "90807060504030201popa"}
]

# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class AuthState(StatesGroup):
    waiting_login = State()
    waiting_register = State()

# ============================================
# БАЗА ДАННЫХ
# ============================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE,
            password TEXT,
            license_key TEXT,
            subscription_status TEXT DEFAULT 'inactive',
            subscription_end DATE,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT,
            telegram_id INTEGER UNIQUE
        )
    ''')
    
    # Таблица платежей
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount INTEGER,
            status TEXT,
            created_at TEXT
        )
    ''')
    
    # Создаём админа, если нет
    admin_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    c.execute('SELECT * FROM users WHERE login = ?', (ADMIN_LOGIN,))
    if not c.fetchone():
        c.execute('''
            INSERT INTO users (login, password, subscription_status, is_admin, created_at)
            VALUES (?, ?, 'active', 1, ?)
        ''', (ADMIN_LOGIN, admin_hash, datetime.now().isoformat()))
        print(f"✅ Админ создан: {ADMIN_LOGIN}")
    
    # Создаём дополнительные аккаунты
    for acc in EXTRA_ACCOUNTS:
        pass_hash = hashlib.sha256(acc["password"].encode()).hexdigest()
        c.execute('SELECT * FROM users WHERE login = ?', (acc["login"],))
        if not c.fetchone():
            c.execute('''
                INSERT INTO users (login, password, subscription_status, is_admin, created_at)
                VALUES (?, ?, 'active', 0, ?)
            ''', (acc["login"], pass_hash, datetime.now().isoformat()))
            print(f"✅ Аккаунт создан: {acc['login']}")
    
    conn.commit()
    conn.close()
    print("✅ База данных готова")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(login, password, telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = hash_password(password)
    try:
        c.execute('''
            INSERT INTO users (login, password, telegram_id, subscription_status, created_at)
            VALUES (?, ?, ?, 'inactive', ?)
        ''', (login, password_hash, telegram_id, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(login, password, telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('SELECT * FROM users WHERE login = ? AND password = ?', (login, password_hash))
    user = c.fetchone()
    if user:
        c.execute('UPDATE users SET telegram_id = ? WHERE login = ?', (telegram_id, login))
        conn.commit()
    conn.close()
    return user

def get_user_by_telegram(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_login(login):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE login = ?', (login,))
    user = c.fetchone()
    conn.close()
    return user

def activate_subscription(telegram_id, license_key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET subscription_status = 'active', 
            license_key = ?,
            subscription_end = ?
        WHERE telegram_id = ?
    ''', (license_key, (datetime.now() + timedelta(days=365*10)).isoformat(), telegram_id))
    conn.commit()
    conn.close()

def save_payment(payment_id, user_id, amount, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO payments (payment_id, user_id, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (payment_id, user_id, amount, status, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def generate_license():
    return f"AVEND-MC-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"

def has_loader():
    return os.path.exists(LOADER_PATH)

# ============================================
# КЛАВИАТУРЫ
# ============================================

def main_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton(text="🔑 Вход", callback_data="login")],
        [InlineKeyboardButton(text="📝 Регистрация", callback_data="register")],
        [InlineKeyboardButton(text="📥 Скачать лоадер", callback_data="download")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="👑 Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def after_login_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton(text="💎 Купить подписку (200⭐)", callback_data="buy")],
        [InlineKeyboardButton(text="📥 Скачать лоадер", callback_data="download")],
        [InlineKeyboardButton(text="🚪 Выйти", callback_data="logout")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="👑 Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_find")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

# ============================================
# БОТ
# ============================================

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_user_by_telegram(message.from_user.id)
    if user:
        is_admin = user[7] == 1
        await message.answer(
            f"👋 С возвращением, {user[1]}!\n"
            f"📅 Статус: {'✅ Активна' if user[4] == 'active' else '❌ Не активна'}\n"
            f"⏱️ Действует до: {user[5] or 'Не куплена'}",
            reply_markup=after_login_keyboard(is_admin=is_admin)
        )
    else:
        await message.answer(
            "🎮 <b>AvendDLC Minecraft</b>\n\n"
            "🔥 Чит для Minecraft 1.21.8\n\n"
            "👇 Войди или зарегистрируйся:",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

@dp.callback_query(F.data == "login")
async def login_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔑 Введите логин и пароль в формате:\n`логин:пароль`\n\nПример: `avenduser0:1234`", parse_mode="Markdown")
    await state.set_state(AuthState.waiting_login)
    await callback.answer()

@dp.callback_query(F.data == "register")
async def register_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите логин и пароль в формате:\n`логин:пароль`\n\nПример: `avenduser0:1234`", parse_mode="Markdown")
    await state.set_state(AuthState.waiting_register)
    await callback.answer()

@dp.message(AuthState.waiting_login)
async def process_login(message: types.Message, state: FSMContext):
    try:
        login, password = message.text.split(":")
        user = login_user(login, password, message.from_user.id)
        if user:
            is_admin = user[7] == 1
            await message.answer(
                f"✅ Добро пожаловать, {login}!\n"
                f"📅 Статус подписки: {'✅ Активна' if user[4] == 'active' else '❌ Не активна'}\n"
                f"⏱️ Действует до: {user[5] or 'Не куплена'}",
                reply_markup=after_login_keyboard(is_admin=is_admin)
            )
        else:
            await message.answer("❌ Неверный логин или пароль. Попробуйте снова /start")
        await state.clear()
    except:
        await message.answer("❌ Неверный формат. Используйте: `логин:пароль`", parse_mode="Markdown")

@dp.message(AuthState.waiting_register)
async def process_register(message: types.Message, state: FSMContext):
    try:
        login, password = message.text.split(":")
        
        existing = get_user_by_login(login)
        if existing:
            await message.answer("❌ Пользователь с таким логином уже существует!")
            await state.clear()
            return
        
        if register_user(login, password, message.from_user.id):
            await message.answer(f"✅ Регистрация прошла успешно!\nДобро пожаловать, {login}!\n\nЧтобы получить доступ, купите подписку за 200⭐", reply_markup=after_login_keyboard())
        else:
            await message.answer("❌ Ошибка регистрации. Возможно, логин уже занят.")
        await state.clear()
    except:
        await message.answer("❌ Неверный формат. Используйте: `логин:пароль`", parse_mode="Markdown")

@dp.callback_query(F.data == "logout")
async def logout(callback: types.CallbackQuery):
    await callback.message.answer("🚪 Вы вышли из системы. Для входа нажмите /start", reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back(callback: types.CallbackQuery):
    user = get_user_by_telegram(callback.from_user.id)
    if user:
        is_admin = user[7] == 1
        await callback.message.edit_text(
            "🎮 Главное меню:",
            reply_markup=after_login_keyboard(is_admin=is_admin)
        )
    else:
        await callback.message.edit_text(
            "🎮 Главное меню:",
            reply_markup=main_keyboard()
        )
    await callback.answer()

@dp.callback_query(F.data == "buy")
async def buy_callback(callback: types.CallbackQuery):
    user = get_user_by_telegram(callback.from_user.id)
    if not user:
        await callback.answer("Сначала войдите в систему!", show_alert=True)
        return
    
    if user[4] == 'active':
        await callback.answer("У вас уже есть активная подписка!", show_alert=True)
        return
    
    payment_id = f"PAY_{user[0]}_{int(datetime.now().timestamp())}"
    save_payment(payment_id, user[0], PRICE_STARS, "pending")
    
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

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    if pre_checkout_q.invoice_payload.startswith("PAY_"):
        await pre_checkout_q.answer(ok=True)
        payment_id = pre_checkout_q.invoice_payload
        user_id = int(payment_id.split("_")[1])
        save_payment(payment_id, user_id, PRICE_STARS, "completed")
        print(f"✅ Платёж принят: {payment_id}")
    else:
        await pre_checkout_q.answer(ok=False, error_message="Ошибка платежа")

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    user_id = int(payment.invoice_payload.split("_")[1])
    
    license_key = generate_license()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT telegram_id FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        telegram_id = result[0]
        activate_subscription(telegram_id, license_key)
        
        await message.answer(
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"🔑 <b>Твой ключ:</b> <code>{license_key}</code>\n\n"
            f"📥 Нажми «Скачать лоадер» в главном меню",
            parse_mode="HTML",
            reply_markup=after_login_keyboard()
        )

@dp.callback_query(F.data == "download")
async def download_callback(callback: types.CallbackQuery):
    if has_loader():
        with open(LOADER_PATH, 'rb') as f:
            await callback.message.reply_document(
                document=types.BufferedInputFile(f.read(), filename="AvendDLC_Loader.exe"),
                caption="📥 <b>AvendDLC Loader</b>\n\n"
                        "1. Запустите от администратора\n"
                        "2. Введите лицензионный ключ\n"
                        "3. Нажмите Inject\n"
                        "4. Запустите Minecraft 1.21.8\n\n"
                        "⚠️ Обязательно запускайте от имени администратора",
                parse_mode="HTML"
            )
        await callback.answer("✅ Лоадер отправлен!")
    else:
        await callback.answer("❌ Лоадер не найден. Напишите @AvendSupport", show_alert=True)

# ============================================
# АДМИН ПАНЕЛЬ
# ============================================

@dp.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery):
    user = get_user_by_telegram(callback.from_user.id)
    if not user or user[7] != 1:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 <b>Админ панель</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    user = get_user_by_telegram(callback.from_user.id)
    if not user or user[7] != 1:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, login, subscription_status, subscription_end, is_admin FROM users')
    users = c.fetchall()
    conn.close()
    
    text = "📊 <b>Все пользователи:</b>\n\n"
    for u in users:
        admin_tag = " 👑" if u[4] == 1 else ""
        text += f"🆔 {u[0]} | {u[1]}{admin_tag} | {u[2]} | {u[3] or 'Нет'}\n"
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_find")
async def admin_find(callback: types.CallbackQuery):
    await callback.message.answer("Введите логин пользователя для поиска:")
    await callback.answer()

# ============================================
# ЗАПУСК
# ============================================

async def main():
    print("🤖 AvendDLC бот запущен!")
    init_db()
    print("✅ Бот готов!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
