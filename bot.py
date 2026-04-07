import os
import sqlite3
import uuid
from datetime import datetime
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram import F

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit(1)

PRICE_STARS = 200
PRODUCT_NAME = "AvendDLC Minecraft Cheat"
PRODUCT_DESCRIPTION = "Чит для Minecraft 1.21.8 | Навсегда"

LOADER_PATH = "loader.exe"

# ============================================
# БАЗА ДАННЫХ
# ============================================

def init_db():
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            license_key TEXT,
            purchase_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount INTEGER,
            status TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова")

def save_user(user_id, username, license_key):
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)',
              (user_id, username, license_key, datetime.now().isoformat(), 'active'))
    conn.commit()
    conn.close()

def save_payment(payment_id, user_id, amount, status):
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO payments VALUES (?, ?, ?, ?, ?)',
              (payment_id, user_id, amount, status, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def generate_license():
    return f"AVEND-MC-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"

def has_loader():
    return os.path.exists(LOADER_PATH)

# ============================================
# КЛАВИАТУРЫ
# ============================================

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить (200⭐)", callback_data="buy")],
        [InlineKeyboardButton(text="📥 Скачать лоадер", callback_data="download")]
    ])

# ============================================
# БОТ
# ============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = """
🎮 <b>AvendDLC Minecraft Cheat</b>

<b>🔥 Чит для Minecraft 1.21.8</b>

<b>⚡ Функции:</b>
• ESP, Aimbot, Fly, Speed
• X-Ray, FullBright, NoFall
• AutoFarm, AntiAFK

<b>💰 Цена: 200 🌟 НАВСЕГДА</b>

👇 Выбери действие:
"""
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())

@dp.callback_query(F.data == "buy")
async def buy_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    # Проверяем, есть ли уже лицензия
    user = get_user(user_id)
    if user:
        await callback.answer("У вас уже есть активная лицензия!", show_alert=True)
        await callback.message.answer(
            f"✅ У вас есть лицензия!\n🔑 Ключ: <code>{user[2]}</code>",
            parse_mode="HTML"
        )
        return
    
    payment_id = f"PAY_{user_id}_{int(datetime.now().timestamp())}"
    save_payment(payment_id, user_id, PRICE_STARS, "pending")
    
    await bot.send_invoice(
        chat_id=user_id,
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
    await callback.message.answer(f"💎 Оплата {PRICE_STARS}⭐ отправлена! Подтвердите в появившемся окне.")

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    if pre_checkout_q.invoice_payload.startswith("PAY_"):
        await pre_checkout_q.answer(ok=True)
        save_payment(pre_checkout_q.invoice_payload, pre_checkout_q.from_user.id, PRICE_STARS, "completed")
        print(f"✅ Платёж принят: {pre_checkout_q.invoice_payload}")
    else:
        await pre_checkout_q.answer(ok=False, error_message="Ошибка платежа")

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    license_key = generate_license()
    save_user(user_id, username, license_key)
    save_payment(payment.invoice_payload, user_id, PRICE_STARS, "success")
    
    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"🔑 <b>Твой ключ:</b> <code>{license_key}</code>\n\n"
        f"📥 Нажми «Скачать лоадер» в главном меню",
        parse_mode="HTML",
        reply_markup=main_keyboard()
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
        await callback.answer("❌ Лоадер временно недоступен", show_alert=True)

# ============================================
# ЗАПУСК
# ============================================

async def main():
    init_db()
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
