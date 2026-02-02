# bot.py
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import Database
from config import Config

db = Database()
SIX_DIGITS_PATTERN = re.compile(r'^\d{6}')


def format_user_info(user):
    """Форматирует информацию о пользователе"""
    parts = []
    if user.first_name:
        parts.append(user.first_name)
    if user.last_name:
        parts.append(user.last_name)
    if user.username:
        parts.append(f'@{user.username}')
    return ' '.join(parts) if parts else 'Anonymous'


def is_authorized(user_id):
    """Проверяет, авторизован ли пользователь"""
    return user_id in Config.AUTHORIZED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем авторизацию только в приватных чатах
    if update.effective_chat.type == 'private' and not is_authorized(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    await update.message.reply_text(
        "Добро пожаловать! Я бот для мониторинга сообщений.\n"
        "Отправьте сообщение, начинающееся с 6 цифр."
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем авторизацию только в приватных чатах
    if update.effective_chat.type == 'private' and not is_authorized(update.effective_user.id):
        return

    message = update.message

    if message.text and SIX_DIGITS_PATTERN.match(message.text):
        code = message.text[:6]  # Извлекаем 6 цифр

        # Получаем комментарий (сообщение без 6 цифр)
        comment = message.text[6:].strip()

        # Форматируем информацию о пользователе
        user_info = format_user_info(message.from_user)

        # Получаем название группы
        chat_title = message.chat.title or "Private Chat"

        # Сохраняем в базу с проверкой на дубликаты
        if db.insert_message(code, user_info, chat_title, comment):
            await message.reply_text("Код сохранен в базе данных!")
        else:
            await message.reply_text("Это сообщение уже было сохранено в течение последних 2 часов.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Ошибка: {context.error}")


def main():
    print('Бот запущен')
    application = Application.builder().token(Config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.ALL, error_handler))

    application.run_polling()


if __name__ == '__main__':
    main()