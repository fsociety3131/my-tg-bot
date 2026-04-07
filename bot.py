import os
import sqlite3
import uuid
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    PreCheckoutQueryHandler,
    MessageHandler, 
    filters, 
    ContextTypes
)

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в переменных окружения!")
    print("👉 Установи: set BOT_TOKEN=ваш_токен")
    exit(1)

PRICE_STARS = 200
PRODUCT_NAME = "AvendDLC Minecraft Cheat"
PRODUCT_DESCRIPTION = "Чит для Minecraft 1.21.8 | Навсегда"

# Путь к лоадеру
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
    print("✅ База данных инициализирована")

def save_user(user_id: int, username: str, license_key: str):
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (user_id, username, license_key, purchase_date, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, license_key, datetime.now().isoformat(), 'active'))
    conn.commit()
    conn.close()

def save_payment(payment_id: str, user_id: int, amount: int, status: str):
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO payments (payment_id, user_id, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (payment_id, user_id, amount, status, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect('avenddlc.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def generate_license() -> str:
    return f"AVEND-MC-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"

def has_loader() -> bool:
    return os.path.exists(LOADER_PATH)

# ============================================
# КЛАВИАТУРЫ
# ============================================

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💎 Купить AvendDLC (200⭐)", callback_data="buy")],
        [InlineKeyboardButton("📥 Скачать лоадер", callback_data="download")],
        [InlineKeyboardButton("📖 Инструкция", callback_data="info")],
        [InlineKeyboardButton("🔑 Проверить лицензию", callback_data="check")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ Оплатить 200 звёзд", callback_data="pay_stars")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================
# ОБРАБОТЧИКИ
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    welcome_text = f"""
🎮 <b>AvendDLC Minecraft Cheat</b>

Привет, {user.first_name}!

<b>🔥 Чит для Minecraft 1.21.8</b>

<b>⚡ Функции:</b>
• ESP (Box, Name, Health, Items)
• Aimbot (Head/Body)
• Fly / Speed / BHop
• NoFall / NoKnockback
• X-Ray / FullBright
• AutoFarm / AutoMine
• AntiAFK
• И многое другое...

<b>💰 Цена: 200 🌟 (Telegram Stars)</b>
<b>⏱️ Срок: НАВСЕГДА</b>

👇 <b>Выбери действие:</b>
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    if query.data == "buy":
        user = get_user(user_id)
        if user:
            await query.edit_message_text(
                f"✅ У вас уже есть активная лицензия!\n\n🔑 Ключ: <code>{user[2]}</code>\n📅 Куплена: {user[3]}",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
            return
        
        buy_text = f"""
💎 <b>Покупка AvendDLC Minecraft Cheat</b>

<b>Товар:</b> {PRODUCT_NAME}
<b>Цена:</b> {PRICE_STARS} 🌟
<b>Срок:</b> навсегда
<b>Версия:</b> Minecraft 1.21.8

<b>Что вы получите после оплаты:</b>
• Лицензионный ключ
• Ссылку на скачивание лоадера
• Доступ ко всем функциям

Нажмите кнопку ниже для оплаты
"""
        await query.edit_message_text(
            buy_text,
            parse_mode="HTML",
            reply_markup=get_payment_keyboard()
        )
    
    elif query.data == "pay_stars":
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
            need_shipping_address=False,
            is_flexible=False,
            protect_content=True
        )
        
        await query.edit_message_text(
            f"⭐ <b>Платёж отправлен!</b>\n\n"
            f"Сумма: {PRICE_STARS} 🌟\n"
            f"Товар: {PRODUCT_NAME}\n\n"
            f"Подтвердите платёж в появившемся окне.",
            parse_mode="HTML"
        )
    
    elif query.data == "download":
        if has_loader():
            with open(LOADER_PATH, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename="AvendDLC_Loader.exe",
                    caption="📥 <b>AvendDLC Loader</b>\n\n"
                            "1. Запустите loader.exe\n"
                            "2. Введите лицензионный ключ\n"
                            "3. Нажмите 'Inject'\n"
                            "4. Запустите Minecraft 1.21.8\n\n"
                            "⚠️ Запускайте от имени администратора",
                    parse_mode="HTML"
                )
            await query.answer("✅ Лоадер отправлен!")
        else:
            await query.answer("❌ Лоадер временно недоступен", show_alert=True)
    
    elif query.data == "info":
        info_text = """
📖 <b>Инструкция по установке AvendDLC</b>

1️⃣ <b>Оплатите подписку</b>
   • Нажмите "Купить"
   • Оплатите 200 Telegram Stars

2️⃣ <b>Скачайте лоадер</b>
   • Используйте кнопку "Скачать лоадер"

3️⃣ <b>Запустите лоадер</b>
   • Запустите от имени администратора
   • Введите полученный ключ

4️⃣ <b>Запустите Minecraft 1.21.8</b>
   • Зайдите на любой сервер
   • Нажмите INSERT для открытия меню

<b>⚙️ Управление:</b>
• INSERT - открыть/закрыть GUI
• DELETE - выгрузить чит

<b>❓ Поддержка:</b>
• @AvendSupport - по всем вопросам
"""
        await query.edit_message_text(
            info_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif query.data == "check":
        user = get_user(user_id)
        if user:
            check_text = f"""
✅ <b>Лицензия активна!</b>

🔑 <b>Ваш ключ:</b> <code>{user[2]}</code>
📅 <b>Дата покупки:</b> {user[3]}
👤 <b>Пользователь:</b> @{username}
⏱️ <b>Статус:</b> {user[4].upper()}
📦 <b>Товар:</b> {PRODUCT_NAME}

💾 <b>Скачать лоадер:</b> кнопка ниже
"""
        else:
            check_text = """
❌ <b>Лицензия не найдена</b>

У вас нет активной подписки.

💰 <b>Купить AvendDLC:</b> 200 🌟 навсегда
Нажмите "Купить" для оформления
"""
        await query.edit_message_text(
            check_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif query.data == "back":
        await query.edit_message_text(
            "🎮 <b>Главное меню AvendDLC</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

# ============================================
# ОБРАБОТКА ПЛАТЕЖЕЙ
# ============================================

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    user_id = query.from_user.id
    
    if query.invoice_payload.startswith("PAY_"):
        await query.answer(ok=True)
        save_payment(query.invoice_payload, user_id, PRICE_STARS, "completed")
        print(f"✅ Платеж принят: {query.invoice_payload}")
    else:
        await query.answer(ok=False, error_message="Ошибка платежа. Попробуйте снова.")

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    license_key = generate_license()
    save_user(user_id, username, license_key)
    save_payment(payment.invoice_payload, user_id, PRICE_STARS, "success")
    
    success_text = f"""
✅ <b>Оплата прошла успешно!</b>

🎉 Спасибо за покупку AvendDLC!

<b>Ваши данные:</b>
📦 Товар: {PRODUCT_NAME}
⏱️ Срок: навсегда
🔑 <b>Лицензионный ключ:</b> 
<code>{license_key}</code>

<b>📥 Скачать лоадер:</b>
Нажмите кнопку "Скачать лоадер" в главном меню

<b>📖 Инструкция:</b>
1. Скачайте лоадер
2. Запустите от администратора
3. Введите ключ: <code>{license_key}</code>
4. Нажмите Inject
5. Запустите Minecraft 1.21.8

❓ Вопросы: @AvendSupport
"""
    
    await update.message.reply_text(
        success_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

# ============================================
# ЗАПУСК
# ============================================

def main():
    print("🤖 Запуск AvendDLC Telegram бота...")
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    print("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
