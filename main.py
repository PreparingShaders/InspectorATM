import re
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from database import Database
from keyboards import Keyboards
from config import Config

db = Database()
SIX_DIGITS_PATTERN = re.compile(r'^\d{6}')


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def is_authorized(user_id):
    return user_id in Config.AUTHORIZED_USERS


def format_user_info(user):
    parts = [user.first_name, user.last_name, f'@{user.username}' if user.username else None]
    return ' '.join(filter(None, parts)) or 'Anonymous'


async def send_report_chunk(message, data, period_name):
    if not data:
        await message.reply_text(f"За период ({period_name}) записей нет.", reply_markup=Keyboards.back_to_main())
        return

    report = f"📋 **{period_name}:**\n\n"

    for row in data[:15]:
        # Парсим дату из БД и переводим в ДД.ММ.ГГГГ
        try:
            raw_date = datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M:%S')
            clean_date = raw_date.strftime('%d.%m.%Y')
        except:
            clean_date = row['datetime'][:10]  # если формат вдруг другой

        # Убираем дубль ATM ID (он и так в заголовке), пишем дату, чат и инженера
        report += f"🗓 {clean_date} | 📍 {row['chat_title']} | 👤 {row['user_info']}\n"

    if len(data) > 15:
        report += f"\n...и еще {len(data) - 15} записей."

    await message.reply_text(report, reply_markup=Keyboards.back_to_main(), parse_mode='Markdown')

async def send_stats_report(message, period_label, date_from, date_to):
    stats = db.get_stats_by_chat(date_from, date_to)
    if not stats:
        await message.reply_text(f"За период {period_label} работ не найдено.", reply_markup=Keyboards.back_to_main())
        return

    total_all = sum(count for chat, count in stats)
    report = f"📊 **Отчет по профилактикам**\n"
    report += f"📅 Период: {period_label}\n"
    report += f"━━━━━━━━━━━━━━━━━━\n"
    for chat, count in stats:
        report += f"📍 {chat}: **{count}**\n"
    report += f"━━━━━━━━━━━━━━━━━━\n"
    report += f"ИТОГО: **{total_all}** работ(ы)"

    await message.reply_text(report, reply_markup=Keyboards.back_to_main(), parse_mode='Markdown')


async def export_to_excel(message):
    try:
        data = db.search_messages()
        if not data:
            await message.reply_text("База пуста.")
            return

        df = pd.DataFrame(data)
        # Порядок в твоей новой базе: id, datetime, atm_id, user_info, chat_title, comment
        df.columns = ['ID', 'Дата и время', 'ID Банкомата', 'Исполнитель', 'Группа/Чат', 'Комментарий']

        file_name = f"report_{datetime.now().strftime('%d_%m_%Y_%H%M')}.xlsx"
        df.to_excel(file_name, index=False)

        with open(file_name, 'rb') as f:
            await message.reply_document(document=f, filename=file_name, caption=f"📊 Записей: {len(df)}")
        os.remove(file_name)
    except Exception as e:
        await message.reply_text(f"❌ Ошибка Excel: {e}")


# --- ВОТ ЭТОЙ ФУНКЦИИ НЕ ХВАТАЛО ---
async def import_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id): return

    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    file_path = "temp_import.json"
    await file.download_to_drive(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        messages_found = 0
        chat_title = data.get('name', 'Импорт из JSON')

        for msg in data.get('messages', []):
            if msg.get('type') != 'message': continue

            raw_text = msg.get('text', "")
            text = ""
            if isinstance(raw_text, list):
                for part in raw_text:
                    text += part.get('text', '') if isinstance(part, dict) else str(part)
            else:
                text = str(raw_text)

            if text and SIX_DIGITS_PATTERN.match(text):
                atm_id = text.strip()[:6]
                comment = text.strip()[6:].strip()
                user_name = msg.get('from', 'Unknown')
                date_iso = msg.get('date', '').replace('T', ' ')

                db.insert_history_message(atm_id, user_name, chat_title, comment, date_iso)
                messages_found += 1

        await update.message.reply_text(f"✅ Импорт завершен! Добавлено: **{messages_found}**")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка импорта: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)


# --- ОБРАБОТЧИКИ ---

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id): return
    await update.message.reply_text("🛠 **Панель управления отчетами**", reply_markup=Keyboards.admin_main(),
                                    parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'admin_main':
        await query.edit_message_text("🛠 **Панель управления**", reply_markup=Keyboards.admin_main(),
                                      parse_mode='Markdown')
    elif query.data == 'stats_week':
        # Ровно 7 дней назад от текущей секунды
        date_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        date_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await send_stats_report(query.message, "за последние 7 дней", date_start, date_end)

    elif query.data == 'stats_month':
        # Ровно 30 дней назад
        date_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        date_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await send_stats_report(query.message, "за последние 30 дней", date_start, date_end)

    elif query.data == 'stats_quarter':
        # Ровно 90 дней назад (так надежнее, чем высчитывать календарный квартал)
        date_start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
        date_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await send_stats_report(query.message, "за последние 90 дней", date_start, date_end)

    elif query.data == 'export_excel':
        await export_to_excel(query.message)
    elif query.data == 'search_date':
        context.user_data['state'] = 'WAIT_DATE_START'
        await query.message.reply_text("📅 Шаг 1: Введите ДАТУ НАЧАЛА (ДД.ММ.ГГГГ):")
    elif query.data == 'search_atm':
        context.user_data['state'] = 'WAIT_ATM_ID'
        await query.message.reply_text("🔍 Введите 6 цифр ID банкомата:")
    elif query.data == 'search_chat':
        context.user_data['state'] = 'WAIT_CHAT_TITLE'
        await query.message.reply_text("🔍 Введите название чата:")
    elif query.data == 'import_json':
        await query.message.reply_text("📥 Пришлите файл `result.json` для импорта.",
                                       reply_markup=Keyboards.back_to_main())


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private' and not is_authorized(update.effective_user.id): return

    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""
    state = context.user_data.get('state')

    if text == "📊 Панель управления":
        await admin_menu(update, context)
        return

    if state == 'WAIT_DATE_START':
        try:
            dt = datetime.strptime(text, '%d.%m.%Y')
            context.user_data['date_start'] = dt.strftime('%Y-%m-%d 00:00:00')
            context.user_data['state'] = 'WAIT_DATE_END'
            await update.message.reply_text(f"✅ Начало: {text}. Введите ДАТУ ОКОНЧАНИЯ (ДД.ММ.ГГГГ):")
        except:
            await update.message.reply_text("❌ Ошибка! Формат: 01.01.2026")
        return

    if state == 'WAIT_DATE_END':
        try:
            dt = datetime.strptime(text, '%d.%m.%Y')
            date_end = dt.strftime('%Y-%m-%d 23:59:59')
            date_start = context.user_data.get('date_start')
            context.user_data['state'] = None
            await send_stats_report(update.message, f"с {date_start[:10]} по {text}", date_start, date_end)
        except:
            await update.message.reply_text("❌ Ошибка! Формат: 01.01.2026")
        return

    if state == 'WAIT_ATM_ID':
        context.user_data['state'] = None
        results = db.search_messages(atm_id=text)
        await send_report_chunk(update.message, results, f"по ATM {text}")
        return

    if state == 'WAIT_CHAT_TITLE':
        context.user_data['state'] = None
        results = db.search_messages(chat_title=text)
        await send_report_chunk(update.message, results, f"по чату {text}")
        return

    if text and SIX_DIGITS_PATTERN.match(text):
        atm_id = text[:6]
        comment = text[6:].strip()
        user_info = format_user_info(update.message.from_user)
        chat_title = update.message.chat.title or "Private Chat"
        if db.insert_message(atm_id, user_info, chat_title, comment):
            await update.message.reply_text(f"✅ Банкомат {atm_id} внесен.")
        else:
            await update.message.reply_text(f"❌ Ошибка: дубликат (пауза 2ч).")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.effective_chat.type == 'private' and not is_authorized(user_id):
        await update.message.reply_text("Нет доступа.")
        return
    await update.message.reply_text("Бот запущен.", reply_markup=Keyboards.main_admin_reply())


def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_menu))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обработчик документов .json
    application.add_handler(MessageHandler(filters.Document.FileExtension("json"), import_history_handler))

    # Обработчик текста
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print('Бот запущен')
    application.run_polling()


if __name__ == '__main__':
    main()