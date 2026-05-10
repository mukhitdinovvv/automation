from __future__ import annotations

import sys

import telebot

from app.bot.handlers import BotHandlers
from app.config import get_settings
from app.services.ai import AssistantService
from app.services.airtable import AirtableClient
from app.services.documents import DocumentService
from app.services.repository import Repository


def build_bot() -> telebot.TeleBot:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is required')
    bot = telebot.TeleBot(settings.telegram_bot_token, parse_mode='HTML')
    airtable = AirtableClient(settings)
    repository = Repository(airtable, settings)
    assistant = AssistantService(settings)
    documents = DocumentService(settings)
    BotHandlers(bot, settings, repository, assistant, documents)
    return bot


def main() -> int:
    bot = build_bot()
    print('Bot started. Press Ctrl+C to stop.')
    bot.infinity_polling(skip_pending=True, timeout=30)
    return 0


if __name__ == '__main__':
    sys.exit(main())
