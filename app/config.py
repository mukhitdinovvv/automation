from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo



def load_dotenv_file(path: str = '.env') -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('\"').strip("'"))


load_dotenv_file()


def _csv_ints(value: str) -> list[int]:
    result: list[int] = []
    for part in value.split(','):
        part = part.strip()
        if part:
            result.append(int(part))
    return result


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    admin_telegram_ids: list[int]
    accountant_telegram_ids: list[int]
    manager_contact: str
    airtable_api_key: str
    airtable_base_id: str
    airtable_clients_table: str = 'Clients'
    airtable_products_table: str = 'Products'
    airtable_suppliers_table: str = 'Suppliers'
    airtable_orders_table: str = 'Orders'
    airtable_order_items_table: str = 'Order_Items'
    airtable_drivers_table: str = 'Drivers'
    airtable_routes_table: str = 'Routes'
    airtable_invoices_table: str = 'Invoices'
    order_cutoff_hour: int = 0
    timezone: str = 'Asia/Almaty'
    default_delivery_days_after_cutoff: int = 2
    public_base_url: str = ''
    documents_dir: Path = Path('documents')
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def get_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
        admin_telegram_ids=_csv_ints(os.getenv('ADMIN_TELEGRAM_IDS', '')),
        accountant_telegram_ids=_csv_ints(os.getenv('ACCOUNTANT_TELEGRAM_IDS', '')),
        manager_contact=os.getenv('MANAGER_CONTACT', '@manager'),
        airtable_api_key=os.getenv('AIRTABLE_API_KEY', ''),
        airtable_base_id=os.getenv('AIRTABLE_BASE_ID', ''),
        airtable_clients_table=os.getenv('AIRTABLE_CLIENTS_TABLE', 'Clients'),
        airtable_products_table=os.getenv('AIRTABLE_PRODUCTS_TABLE', 'Products'),
        airtable_suppliers_table=os.getenv('AIRTABLE_SUPPLIERS_TABLE', 'Suppliers'),
        airtable_orders_table=os.getenv('AIRTABLE_ORDERS_TABLE', 'Orders'),
        airtable_order_items_table=os.getenv('AIRTABLE_ORDER_ITEMS_TABLE', 'Order_Items'),
        airtable_drivers_table=os.getenv('AIRTABLE_DRIVERS_TABLE', 'Drivers'),
        airtable_routes_table=os.getenv('AIRTABLE_ROUTES_TABLE', 'Routes'),
        airtable_invoices_table=os.getenv('AIRTABLE_INVOICES_TABLE', 'Invoices'),
        order_cutoff_hour=int(os.getenv('ORDER_CUTOFF_HOUR', '0')),
        timezone=os.getenv('TIMEZONE', 'Asia/Almaty'),
        default_delivery_days_after_cutoff=int(os.getenv('DEFAULT_DELIVERY_DAYS_AFTER_CUTOFF', '2')),
        public_base_url=os.getenv('PUBLIC_BASE_URL', '').rstrip('/'),
        documents_dir=Path(os.getenv('DOCUMENTS_DIR', 'documents')),
        openai_api_key=os.getenv('OPENAI_API_KEY', ''),
        openai_model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
    )
