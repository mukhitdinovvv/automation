from __future__ import annotations

from telebot import types

from app.models import TIME_WINDOWS


def main_menu() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('🛒 Сделать заказ', '🔁 Мой последний заказ')
    keyboard.add('📜 История заказов', '❓ Помощь')
    keyboard.add('☎️ Связаться с менеджером')
    return keyboard


def admin_menu() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('📊 Отчет за сегодня', '📦 Активные товары')
    keyboard.add('👥 Клиенты', '🚚 Водители')
    return keyboard


def inline_options(prefix: str, options: list[tuple[str, str]], row_width: int = 1) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=row_width)
    buttons = [types.InlineKeyboardButton(label, callback_data=f'{prefix}:{value}') for label, value in options]
    keyboard.add(*buttons)
    return keyboard


def time_keyboard() -> types.InlineKeyboardMarkup:
    return inline_options('time', [(item, item) for item in TIME_WINDOWS], row_width=2)


def yes_no_keyboard(prefix: str) -> types.InlineKeyboardMarkup:
    return inline_options(prefix, [('✅ Да', 'yes'), ('❌ Нет', 'no')], row_width=2)
