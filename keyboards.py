from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from datetime import datetime


class Keyboards:
    @staticmethod
    def main_admin_reply():
        """Постоянные кнопки внизу (Reply)"""
        keyboard = [
            [KeyboardButton("📊 Панель управления")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def admin_main():
        """Обновленное Inline меню"""
        # Определяем текущий квартал для подсказки (опционально)
        month = datetime.now().month
        current_q = (month - 1) // 3 + 1

        keyboard = [
            [
                InlineKeyboardButton("📅 Неделя", callback_data='stats_week'),
                InlineKeyboardButton("📅 Месяц", callback_data='stats_month')
            ],
            [
                InlineKeyboardButton(f"🏢 Квартал (Q{current_q})", callback_data='stats_quarter'),
                InlineKeyboardButton("⌨️ Ввести дату вручную", callback_data='search_date'),
            ],
            [
                InlineKeyboardButton("🔍 Поиск по ATM", callback_data='search_atm'),
                InlineKeyboardButton("💬 Поиск по чату", callback_data='search_chat'),
            ],
            [
                InlineKeyboardButton("📑 Excel отчет", callback_data='export_excel'),
                InlineKeyboardButton("📥 Импорт истории (JSON)", callback_data='import_json')            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_main():
        return InlineKeyboardMarkup([[InlineKeyboardButton("« Назад в меню", callback_data='admin_main')]])