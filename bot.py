import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime, time
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
IMAGE_URL = 'https://i.ibb.co/d0rnQ1Rq/Frame-625.jpg'
ADMIN_ID = 41879842  # Ваш Telegram ID

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
    
    return {
        'total_users': total_users,
        'guide_users': guide_users,
        'total_requests': total_requests
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f'Привет, {use
