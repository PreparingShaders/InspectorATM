import re
import io
from datetime import datetime, timedelta
from typing import List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings, ATM_PATTERN
from database import Report, async_session
from keyboards import get_main_menu
from database import engine  # для экспорта


# FSM состояния для фильтров (когда админ вводит текст)
class AdminStates(StatesGroup):
    waiting_atm_filter = State()
    waiting_chat_filter = State()


# ─── ГРУППОВЫЕ ЧАТЫ (работает везде, без middleware) ───────────────────────

group_router = Router()


@group_router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def catch_atm_report(message: Message):
    """Ловит сообщения с 6 цифрами в группах и сохраняет в БД"""
    if match := re.search(ATM_PATTERN, message.text or ""):
        atm_id = match.group(0)

        async with async_session() as session:
            report = Report(
                user_id=message.from_user.id,
                username=message.from_user.username,
                chat_title=message.chat.title or "Без названия",
                chat_id=message.chat.id,
                atm_id=atm_id,
                message_id=message.message_id,
            )
            session.add(report)
            await session.commit()

        # Уведомление админу (если включено)
        if settings.NOTIFY_ADMIN_ON_NEW_REPORT:
            try:
                await message.bot.send_message(
                    settings.ADMIN_ID,
                    f"🆕 Новый отчёт по АТМ\n"
                    f"ATM: <code>{atm_id}</code>\n"
                    f"Чат: <b>{message.chat.title}</b>\n"
                    f"Автор: {message.from_user.full_name}\n"
                    f"⏰ {message.date.strftime('%H:%M %d.%m')}",
                    parse_mode="HTML"
                )
            except Exception:
                pass  # админ заблокировал бота или другая ошибка


# ─── АДМИН ПАНЕЛЬ (только для ADMIN_ID, с middleware) ─────────────────────

admin_router = Router()
admin_storage = MemoryStorage()  # для FSM


@admin_router.message(commands=["start"])
async def cmd_start(message: Message):
    """Главное меню админа"""
    await message.answer(
        "👋 Добро пожаловать в панель отчётов по АТМ!\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@admin_router.callback_query(F.data.startswith("reports:"))
async def process_report_filter(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопок фильтров"""
    filter_type = callback.data.split(":")[1]

    if filter_type == "today":
        reports = await get_reports_today()
        await send_report_list(callback, reports, "📊 Отчёты за сегодня")

    elif filter_type == "week":
        reports = await get_reports_week()
        await send_report_list(callback, reports, "📊 Отчёты за неделю")

    elif filter_type == "by_atm":
        await callback.message.edit_text("Введите номер АТМ (6 цифр):")
        await state.set_state(AdminStates.waiting_atm_filter)
        await callback.answer()

    elif filter_type == "by_chat":
        await callback.message.edit_text("Введите название чата (или часть):")
        await state.set_state(AdminStates.waiting_chat_filter)
        await callback.answer()

    await callback.answer()


@admin_router.callback_query(F.data == "export:excel")
async def export_to_excel(callback: CallbackQuery):
    """Экспорт всех отчётов в Excel"""
    try:
        async with async_session() as session:
            result = await session.execute(select(Report).order_by(Report.created_at.desc()))
            reports = result.scalars().all()

        if not reports:
            await callback.message.edit_text("Нет данных для экспорта.")
            return

        # Создаём Excel в памяти
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Отчёты по АТМ"

        # Заголовки
        headers = ["ID", "Дата/время", "Пользователь", "Чат", "ATM ID", "Сообщение ID"]
        ws.append(headers)

        # Данные
        for r in reports:
            ws.append([
                r.id,
                r.created_at.strftime("%d.%m.%Y %H:%M"),
                r.username or f"ID{r.user_id}",
                r.chat_title,
                r.atm_id,
                r.message_id
            ])

        # Сохраняем в байты
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        await callback.message.delete()
        await callback.message.bot.send_document(
            callback.from_user.id,
            document=("reports.xlsx", buffer.getvalue(),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        )
        await callback.answer("✅ Excel отправлен!")

    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка экспорта: {str(e)}")
        await callback.answer()


# ─── FSM: обработка текстового ввода фильтров ─────────────────────────────

@admin_router.message(AdminStates.waiting_atm_filter)
async def filter_by_atm(message: Message, state: FSMContext):
    atm_id = message.text.strip()
    if re.match(ATM_PATTERN, atm_id):
        reports = await get_reports_by_atm(atm_id)
        await send_report_list(message, reports, f"📊 Отчёты по АТМ <code>{atm_id}</code>")
    else:
        await message.answer("❌ Неверный формат АТМ (нужно 6 цифр)")

    await state.clear()


@admin_router.message(AdminStates.waiting_chat_filter)
async def filter_by_chat(message: Message, state: FSMContext):
    chat_name = f"%{message.text.strip()}%"
    reports = await get_reports_by_chat(chat_name)
    await send_report_list(message, reports, f"📊 Отчёты по чату: {message.text}")
    await state.clear()


# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ─────────────────────────────────────────────

async def get_reports_today() -> List[Report]:
    """Отчёты за последние 24 часа"""
    cutoff = datetime.utcnow() - timedelta(days=1)
    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.created_at >= cutoff).order_by(Report.created_at.desc())
        )
        return result.scalars().all()


async def get_reports_week() -> List[Report]:
    """Отчёты за последние 7 дней"""
    cutoff = datetime.utcnow() - timedelta(days=7)
    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.created_at >= cutoff).order_by(Report.created_at.desc())
        )
        return result.scalars().all()


async def get_reports_by_atm(atm_id: str) -> List[Report]:
    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.atm_id == atm_id).order_by(Report.created_at.desc())
        )
        return result.scalars().all()


async def get_reports_by_chat(chat_name: str) -> List[Report]:
    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.chat_title.ilike(chat_name)).order_by(Report.created_at.desc())
        )
        return result.scalars().all()


async def send_report_list(event, reports: List[Report], title: str):
    """Форматирует и отправляет список отчётов"""
    if not reports:
        text = f"{title}\n\n❌ Нет данных."
    else:
        text = f"{title}\n\n"
        for r in reports[:20]:  # максимум 20 последних
            username = r.username or f"ID{r.user_id}"
            text += (
                f"⏰ {r.created_at.strftime('%H:%M %d.%m')}\n"
                f"👤 {username}\n"
                f"💬 <b>{r.chat_title}</b>\n"
                f"🏧 <code>{r.atm_id}</code>\n"
                f"🆔 Msg: {r.message_id}\n\n"
            )
        if len(reports) > 20:
            text += f"... и ещё {len(reports) - 20} отчётов. Используйте Excel для полного списка."

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
    else:
        await event.answer(text, parse_mode="HTML")