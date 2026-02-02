# get_id_bot.py
from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or 'no_username'
    first_name = update.effective_user.first_name or ''
    last_name = update.effective_user.last_name or ''

    message = f"""
    Ваш ID: {user_id}
    Username: @{username}
    Имя: {first_name}
    Фамилия: {last_name}
    """

    await update.message.reply_text(message)

def main():
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("Токен не найден в переменных окружения!")
        return

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("id", get_id))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_id))
    application.run_polling()

if __name__ == '__main__':
    main()