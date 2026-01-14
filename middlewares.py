from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from config import settings


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Проверяем наличие from_user (у callback_query и message он есть)
        user_id = getattr(event.from_user, "id", None) if hasattr(event, "from_user") else None

        if user_id != settings.ADMIN_ID:
            if hasattr(event, "answer"):
                await event.answer("Доступ запрещён")
            elif hasattr(event, "answer"):
                await event.answer("Нет прав доступа", show_alert=True)
            return

        return await handler(event, data)