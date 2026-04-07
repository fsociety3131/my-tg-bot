import os
import sqlite3
import uuid
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    print("👉 set BOT_TOKEN=ваш_токен")
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Купить (200⭐)", callback_data="buy")],
        [InlineKeyboardButton("📥 Скачать лоадер", callback_data="download")],
        [InlineKeyboardButton("📖 Инструкция", callback_data="info")],
        [InlineKeyboardButton("🔑 Проверить лицензию", callback_data="check")]
    ])

# ============================================
# ОБРАБОТЧИКИ
# ============================================

async def start(update, context):
    user = update.effective_user
    text = f"""
🎮 <b>AvendDLC Minecraft Cheat</b>

Привет, {user.first_name}!

<b>🔥 Чит для Minecraft 1.21.8</b>

<b>⚡ Функции:</b>
• ESP, Aimbot, Fly, Speed
• X-Ray, FullBright, NoFall
• AutoFarm, AntiAFK

<b>💰 Цена: 200 🌟 НАВСЕГДА</b>

👇 Выбери действие:
"""
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name

    if query.data == "buy":
        user = get_user(user_id)
        if user:
            await query.edit_message_text(
                f"✅ У вас есть лицензия!\n🔑 <code>{user[2]}</code>",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
            return
        
        payment_id = f"PAY_{user_id}_{int(datetime.now().timestamp())}"
        save_payment(payment_id, user_id, PRICE_STARS, "pending")
        
        await context.bot.send_invoice(
            chat_id=user_id,
            title=PRODUCT_NAME,
            description=PRODUCT_DESCRIPTION,
            payload=payment_id,
            currency="XTR",
            prices=[LabeledPrice(PRODUCT_NAME, PRICE_STARS)],
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False
        )
        
        await query.edit_message_text(f"💎 Оплата {PRICE_STARS}⭐ отправлена! Подтвердите в окне.")

    elif query.data == "download":
        if has_loader():
            with open(LOADER_PATH, 'rb') as f:
                await query.message.reply_document(f, filename="AvendDLC_Loader.exe",
                    caption="📥 Запусти от администратора, введи ключ, нажми Inject")
            await query.answer("✅ Лоадер отправлен!")
        else:
            await query.answer("❌ Лоадер временно недоступен", show_alert=True)

    elif query.data == "info":
        await query.edit_message_text(
            "📖 1. Оплати 200⭐\n2. Скачай лоадер\n3. Введи ключ\n4. Запусти Minecraft 1.21.8\n5. Нажми INSERT",
            reply_markup=main_keyboard()
        )

    elif query.data == "check":
        user = get_user(user_id)
        if user:
            await query.edit_message_text(f"✅ Лицензия активна!\n🔑 <code>{user[2]}</code>", parse_mode="HTML", reply_markup=main_keyboard())
        else:
            await query.edit_message_text("❌ Лицензия не найдена. Купи за 200⭐", reply_markup=main_keyboard())

    elif query.data == "back":
        await query.edit_message_text("🎮 Главное меню:", reply_markup=main_keyboard())

async def pre_checkout(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("PAY_"):
        await query.answer(ok=True)
        save_payment(query.invoice_payload, query.from_user.id, PRICE_STARS, "completed")
        print(f"✅ Платёж: {query.invoice_payload}")

async def success_payment(update, context):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    key = generate_license()
    save_user(user_id, username, key)
    save_payment(payment.invoice_payload, user_id, PRICE_STARS, "success")
    
    await update.message.reply_text(
        f"✅ Оплата прошла!\n\n🔑 <b>Твой ключ:</b> <code>{key}</code>\n\n📥 Скачай лоадер кнопкой ниже",
        parse_mode="HTML", reply_markup=main_keyboard()
    )

# ============================================
# ЗАПУСК
# ============================================

def main():
    print("🤖 Запуск...")
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, success_payment))
    
    # PreCheckoutQueryHandler может отсутствовать в старой версии, поэтому оборачиваем
    try:
        from telegram.ext import PreCheckoutQueryHandler
        app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    except ImportError:
        print("⚠️ PreCheckoutQueryHandler не импортирован, но платежи могут работать")
    
    print("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
