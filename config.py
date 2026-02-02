# config.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_PATH = 'messages.db'
    TIMEZONE = 'Europe/Moscow'

    # Парсим JSON строку в список
    AUTHORIZED_USERS = json.loads(os.getenv('AUTHORIZED_USERS', '[]'))