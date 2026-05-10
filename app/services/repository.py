from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from app.config import Settings
from app.models import AirtableRecord, CartItem, OrderDraft
from app.services.airtable import AirtableClient, airtable_string


class Repository:
    def __init__(self, airtable: AirtableClient, settings: Settings) -> None:
        self.airtable = airtable
        self.settings = settings

    def find_client_by_access_code(self, access_code: str) -> AirtableRecord | None:
        formula = f"AND({{access_code}}='{airtable_string(access_code)}', {{status}}='active')"
        return self._first(self.airtable.list_records(self.settings.airtable_clients_table, formula=formula, max_records=1))

    def find_client_by_telegram_id(self, telegram_id: int) -> AirtableRecord | None:
        formula = f"AND({{telegram_id}}={telegram_id}, {{status}}='active')"
        return self._first(self.airtable.list_records(self.settings.airtable_clients_table, formula=formula, max_records=1))

    def bind_client_telegram(self, client_record_id: str, telegram_id: int) -> AirtableRecord:
        return self.airtable.update_record(self.settings.airtable_clients_table, client_record_id, {'telegram_id': telegram_id})

    def reset_client_telegram(self, client_record_id: str) -> AirtableRecord:
        return self.airtable.update_record(self.settings.airtable_clients_table, client_record_id, {'telegram_id': None})

    def list_active_products(self) -> list[AirtableRecord]:
        return self.airtable.list_records(self.settings.airtable_products_table, formula="{status}='active'", sort=[{'field': 'category'}, {'field': 'name'}])

    def list_categories(self) -> list[str]:
        return sorted({str(product.get('category')) for product in self.list_active_products() if product.get('category')})

    def list_products_by_category(self, category: str) -> list[AirtableRecord]:
        formula = f"AND({{status}}='active', {{category}}='{airtable_string(category)}')"
        return self.airtable.list_records(self.settings.airtable_products_table, formula=formula, sort=[{'field': 'name'}])

    def get_product(self, product_record_id: str) -> AirtableRecord:
        return self.airtable.get_record(self.settings.airtable_products_table, product_record_id)

    def list_active_drivers(self) -> list[AirtableRecord]:
        return self.airtable.list_records(self.settings.airtable_drivers_table, formula="{status}='active'", sort=[{'field': 'name'}])

    def find_driver_for_client(self, client: AirtableRecord) -> AirtableRecord | None:
        district = client.get('district')
        drivers = self.list_active_drivers()
        for driver in drivers:
            districts = driver.get('district', [])
            if isinstance(districts, list) and district in districts:
                return driver
        return self._first(drivers)

    def get_supplier(self, supplier_record_id: str) -> AirtableRecord:
        return self.airtable.get_record(self.settings.airtable_suppliers_table, supplier_record_id)

    def create_order(self, draft: OrderDraft) -> AirtableRecord:
        fields = {
            'client_id': [draft.client_record_id],
            'delivery_date': draft.delivery_date.isoformat() if draft.delivery_date else None,
            'delivery_time': draft.delivery_time,
            'comment': draft.comment,
            'status': 'Новый',
            'total_sum': float(draft.total_sum),
        }
        return self.airtable.create_record(self.settings.airtable_orders_table, self._without_none(fields))

    def create_order_items(self, order_record_id: str, items: Iterable[CartItem]) -> list[AirtableRecord]:
        created: list[AirtableRecord] = []
        for item in items:
            created.append(self.airtable.create_record(self.settings.airtable_order_items_table, {
                'order_id': [order_record_id],
                'product_id': [item.product_record_id],
                'quantity': float(item.quantity),
                'price': float(item.price),
            }))
        return created

    def create_route(self, delivery_date: date, client_record_id: str, driver_record_id: str | None) -> AirtableRecord | None:
        if not driver_record_id:
            return None
        return self.airtable.create_record(self.settings.airtable_routes_table, {
            'date': delivery_date.isoformat(),
            'driver_id': [driver_record_id],
            'client_id': [client_record_id],
            'status': 'pending',
        })

    def create_invoice(self, invoice_number: str, order_record_id: str, driver_record_id: str | None, pdf_link: str) -> AirtableRecord:
        fields = {
            'invoice_number': invoice_number,
            'order_id': [order_record_id],
            'driver_id': [driver_record_id] if driver_record_id else None,
            'pdf_link': pdf_link,
            'status': 'created',
        }
        return self.airtable.create_record(self.settings.airtable_invoices_table, self._without_none(fields))

    def latest_order_for_client(self, client_record_id: str) -> AirtableRecord | None:
        formula = f"{{client_id}}='{client_record_id}'"
        return self._first(self.airtable.list_records(self.settings.airtable_orders_table, formula=formula, max_records=1, sort=[{'field': 'date_created', 'direction': 'desc'}]))

    @staticmethod
    def product_to_cart_item(product: AirtableRecord, quantity: Decimal) -> CartItem:
        supplier_ids = product.get('supplier_id', [])
        if not isinstance(supplier_ids, list):
            supplier_ids = []
        return CartItem(
            product_record_id=product.id,
            product_name=str(product.get('name', 'Без названия')),
            unit=str(product.get('unit', 'шт')),
            quantity=quantity,
            price=Decimal(str(product.get('sale_price', 0))),
            supplier_record_ids=supplier_ids,
        )

    @staticmethod
    def _first(records: list[AirtableRecord]) -> AirtableRecord | None:
        return records[0] if records else None

    @staticmethod
    def _without_none(fields: dict[str, object]) -> dict[str, object]:
        return {key: value for key, value in fields.items() if value is not None}
