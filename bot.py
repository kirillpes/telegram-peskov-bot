import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime, time
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
IMAGE_URL = 'https://i.ibb.co/d0rnQ1Rq/Frame-625.jpg'
ADMIN_ID = 41879842

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

def get_stats():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE requested_guide = 1')
    guide_users = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(guide_request_count) FROM users')
    total_requests = cursor.fetchone()[0] or 0
    conn.close()
    return {'total_users': total_users, 'guide_users': guide_users, 'total_requests': total_requests}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(f'Привет, {user.first_name}! 👋\n\nНапиши "гайд" чтобы получить ссылку на руководство.')

async def send_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    mark_guide_requested(user.id)
    message_text = ("держи ссылку на гайд:\nhttps://peskov.notion.site/n8n-28086446fff38053a53ddb47634c41d3?pvs=74\n\nлюбыме идея и предложениям после прочтения не стесняйся адресовать кириллу: @kirillpeskov")
    await update.message.reply_photo(photo=IMAGE_URL, caption=message_text)

async def send_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ У вас нет доступа к этой команде")
        return
    stats = get_stats()
    try:
        with open('bot_users.db', 'rb') as db_file:
            caption = f"📊 Статистика бота:\n\n👥 Всего пользователей: {stats['total_users']}\n✅ Запросили гайд: {stats['guide_users']}\n📈 Всего запросов: {stats['total_requests']}\n\n🗓 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            await update.message.reply_document(document=db_file, filename=f"bot_users_{datetime.now().strftime('%Y%m%d_%H%M')}.db", caption=caption)
        logging.info(f"База данных отправлена админу {user.id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке базы: {e}")
        logging.error(f"Ошибка отправки базы: {e}")

async def daily_backup(context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()
    try:
        with open('bot_users.db', 'rb') as db_file:
            caption = f"🔄 Ежедневный бэкап базы данных\n\n📊 Статистика:\n👥 Всего пользователей: {stats['total_users']}\n✅ Запросили гайд: {stats['guide_users']}\n📈 Всего запросов: {stats['total_requests']}\n\n🗓 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            await context.bot.send_document(chat_id=ADMIN_ID, document=db_file, filename=f"backup_{datetime.now().strftime('%Y%m%d')}.db", caption=caption)
        logging.info("Ежедневный бэкап отправлен")
    except Exception as e:
        logging.error(f"Ошибка при отправке ежедневного бэкапа: {e}")

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getdb", send_database))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^["\']?гайд["\']?$'), send_guide))
    job_queue = application.job_queue
    job_queue.run_daily(daily_backup, time=time(hour=12, minute=0))
    logging.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
