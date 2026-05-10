from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any


DISTRICTS = [
    'Алмалинский',
    'Ауэзовский',
    'Бостандыкский',
    'Жетысуский',
    'Медеуский',
    'Наурызбайский',
    'Турксибский',
]

TIME_WINDOWS = ['06:00-08:00', '08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00']
ORDER_STATUSES = ['Новый', 'Принят', 'Отправлен поставщику', 'В закупке', 'Собран', 'Передан водителю', 'В пути', 'Доставлен', 'Отменен', 'Ошибка']


class Role(str, Enum):
    CLIENT = 'client'
    ADMIN = 'admin'


@dataclass(slots=True)
class AirtableRecord:
    id: str
    fields: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)


@dataclass(slots=True)
class CartItem:
    product_record_id: str
    product_name: str
    unit: str
    quantity: Decimal
    price: Decimal
    supplier_record_ids: list[str]

    @property
    def total(self) -> Decimal:
        return self.quantity * self.price


@dataclass(slots=True)
class OrderDraft:
    client_record_id: str
    delivery_date: date | None = None
    delivery_time: str | None = None
    comment: str = ''
    items: list[CartItem] = field(default_factory=list)
    selected_category: str | None = None

    @property
    def total_sum(self) -> Decimal:
        return sum((item.total for item in self.items), Decimal('0'))

    def as_summary(self) -> str:
        lines = ['🧾 Проверьте заказ:']
        for index, item in enumerate(self.items, start=1):
            lines.append(f'{index}. {item.product_name} — {item.quantity:g} {item.unit} × {item.price:g} ₸ = {item.total:g} ₸')
        lines.append(f'Дата: {self.delivery_date}')
        lines.append(f'Время: {self.delivery_time}')
        if self.comment:
            lines.append(f'Комментарий: {self.comment}')
        lines.append(f'Итого: {self.total_sum:g} ₸')
        return '\n'.join(lines)
