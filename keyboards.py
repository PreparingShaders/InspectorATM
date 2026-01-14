from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu():
    builder = InlineKeyboardBuilder()

    builder.button(text="Сегодня", callback_data="reports:today")
    builder.button(text="Неделя", callback_data="reports:week")
    builder.button(text="Экспорт Excel", callback_data="export:excel")
    builder.button(text="По номеру АТМ", callback_data="reports:by_atm")

    builder.adjust(2, 2)
    return builder.as_markup()