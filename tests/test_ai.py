from datetime import date

from app.config import Settings
from app.services.ai import AssistantService


def test_local_ai_parser_extracts_simple_order():
    settings = Settings(
        telegram_bot_token='token',
        admin_telegram_ids=[],
        accountant_telegram_ids=[],
        manager_contact='@manager',
        airtable_api_key='key',
        airtable_base_id='base',
    )
    parsed = AssistantService(settings).parse_order_text('Нужны 10 молока и 3 сливок на завтра утром', date(2026, 5, 9))
    assert parsed is not None
    assert parsed.delivery_date.isoformat() == '2026-05-10'
    assert parsed.delivery_time == '08:00-10:00'
    assert len(parsed.items) == 2
