from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from app.models import AirtableRecord, OrderDraft
from app.services.repository import Repository


class TelegramSender(Protocol):
    def send_message(self, chat_id: int, text: str, **kwargs: object) -> object:
        ...

    def send_document(self, chat_id: int, document: object, **kwargs: object) -> object:
        ...


class NotificationService:
    def __init__(self, bot: TelegramSender, repository: Repository, accountant_ids: list[int]) -> None:
        self.bot = bot
        self.repository = repository
        self.accountant_ids = accountant_ids

    def notify_suppliers(self, order: AirtableRecord, client: AirtableRecord, draft: OrderDraft) -> None:
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in draft.items:
            for supplier_id in item.supplier_record_ids:
                grouped[supplier_id].append(f'• {item.product_name} — {item.quantity:g} {item.unit}')
        for supplier_id, lines in grouped.items():
            supplier = self.repository.get_supplier(supplier_id)
            telegram_id = supplier.get('telegram_id')
            if telegram_id:
                text = '\n'.join([
                    '📦 Новая заявка',
                    f'Заказ: {order.get("order_id", order.id)}',
                    f'Дата: {draft.delivery_date}',
                    f'Клиент: {client.get("name", "")}',
                    *lines,
                ])
                self.bot.send_message(int(telegram_id), text)

    def notify_driver(self, driver: AirtableRecord | None, client: AirtableRecord, draft: OrderDraft, invoice_link: str) -> None:
        if not driver or not driver.get('telegram_id'):
            return
        items = '\n'.join(f'• {item.product_name} — {item.quantity:g} {item.unit}' for item in draft.items)
        text = '\n'.join([
            '🚚 Новый маршрут',
            f'Клиент: {client.get("name", "")}',
            f'Адрес: {client.get("address", "")}',
            f'Район: {client.get("district", "")}',
            f'Дата/время: {draft.delivery_date} {draft.delivery_time}',
            f'Комментарий: {draft.comment or "—"}',
            'Товары:',
            items,
            f'Накладная: {invoice_link}',
        ])
        self.bot.send_message(int(driver.get('telegram_id')), text)

    def notify_accountants(self, order: AirtableRecord, client: AirtableRecord, draft: OrderDraft, invoice_link: str) -> None:
        for accountant_id in self.accountant_ids:
            text = '\n'.join([
                '📑 Новая накладная',
                f'Заказ: {order.get("order_id", order.id)}',
                f'Клиент: {client.get("name", "")}',
                f'Сумма: {draft.total_sum:g} ₸',
                f'Документ: {invoice_link}',
            ])
            self.bot.send_message(accountant_id, text)
