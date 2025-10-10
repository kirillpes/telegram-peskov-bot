import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = '8387448718:AAE6tEB2wHLljx8Wva0dKeMuK-i6IPGj_sA'
IMAGE_URL = 'https://i.ibb.co/d0rnQ1Rq/Frame-625.jpg'

def init_db():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_interaction TIMESTAMP,
            requested_guide BOOLEAN DEFAULT 0,
            guide_request_count INTEGER DEFAULT 0,
            last_guide_request TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_or_update_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, first_interaction)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, datetime.now()))
        logging.info(f"Новый пользователь: {user_id}")
    conn.commit()
    conn.close()

def mark_guide_requested(user_id):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET requested_guide = 1,
            guide_request_count = guide_request_count + 1,
            last_guide_request = ?
        WHERE user_id = ?
    ''', (datetime.now(), user_id))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f'Привет, {user.first_name}! 👋\n\nНапиши "гайд" чтобы получить ссылку на руководство.'
    )

async def send_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    mark_guide_requested(user.id)
    
    message_text = (
        "держи ссылку на гайд:\n"
        "https://peskov.notion.site/n8n-28086446fff38053a53ddb47634c41d3?pvs=74\n\n"
        "любыме идея и предложениям после прочтения не стесняйся "
        "адресовать кириллу: @kirillpeskov"
    )
    
    await update.message.reply_photo(photo=IMAGE_URL, caption=message_text)

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^гайд$'), send_guide))
    logging.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
