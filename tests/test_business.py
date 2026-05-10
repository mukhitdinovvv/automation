from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import Settings
from app.models import AirtableRecord, OrderDraft
from app.services.business import BusinessRules
from app.services.documents import DocumentService


def test_cutoff_midnight_means_next_day_delivery():
    settings = Settings(
        telegram_bot_token='token',
        admin_telegram_ids=[],
        accountant_telegram_ids=[],
        manager_contact='@manager',
        airtable_api_key='key',
        airtable_base_id='base',
        order_cutoff_hour=0,
        timezone='Asia/Almaty',
    )
    rules = BusinessRules(settings)
    now = datetime(2026, 5, 9, 10, 17, tzinfo=ZoneInfo('Asia/Almaty'))
    assert rules.earliest_delivery_date(now).isoformat() == '2026-05-10'


def test_invoice_html_created(tmp_path: Path):
    settings = Settings(
        telegram_bot_token='token',
        admin_telegram_ids=[],
        accountant_telegram_ids=[],
        manager_contact='@manager',
        airtable_api_key='key',
        airtable_base_id='base',
        documents_dir=tmp_path,
    )
    service = DocumentService(settings)
    order = AirtableRecord(id='recOrder123', fields={'order_id': 42})
    client = AirtableRecord(id='recClient', fields={'name': 'Кофейня №1', 'address': 'Абая 1'})
    draft = OrderDraft(client_record_id='recClient')
    document = service.create_invoice_html(order, client, None, draft)
    assert document.file_path.exists()
    assert 'INV-' in document.invoice_number
    assert 'Кофейня №1' in document.file_path.read_text(encoding='utf-8')
