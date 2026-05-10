from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.models import AirtableRecord, OrderDraft


@dataclass(slots=True)
class InvoiceDocument:
    invoice_number: str
    file_path: Path
    public_link: str


class DocumentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.invoice_dir = settings.documents_dir / 'invoices'
        self.invoice_dir.mkdir(parents=True, exist_ok=True)

    def create_invoice_html(self, order: AirtableRecord, client: AirtableRecord, driver: AirtableRecord | None, draft: OrderDraft) -> InvoiceDocument:
        invoice_number = self.build_invoice_number(order)
        filename = f'{invoice_number}.html'
        file_path = self.invoice_dir / filename
        rows = '\n'.join(
            '<tr>'
            f'<td>{index}</td>'
            f'<td>{html.escape(item.product_name)}</td>'
            f'<td>{item.quantity:g}</td>'
            f'<td>{html.escape(item.unit)}</td>'
            f'<td>{item.price:g} ₸</td>'
            f'<td>{item.total:g} ₸</td>'
            '</tr>'
            for index, item in enumerate(draft.items, start=1)
        )
        driver_name = driver.get('name', 'Не назначен') if driver else 'Не назначен'
        content = f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Накладная {html.escape(invoice_number)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #111827; }}
h1 {{ margin-bottom: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
th {{ background: #f3f4f6; }}
.meta {{ margin-top: 16px; line-height: 1.6; }}
.total {{ margin-top: 20px; text-align: right; font-size: 20px; font-weight: bold; }}
.signatures {{ display: flex; justify-content: space-between; margin-top: 56px; }}
</style>
</head>
<body>
<h1>Накладная № {html.escape(invoice_number)}</h1>
<div class="meta">
Дата создания: {datetime.now(self.settings.tzinfo).strftime('%d.%m.%Y %H:%M')}<br>
Клиент: {html.escape(str(client.get('name', '')))}<br>
Адрес: {html.escape(str(client.get('address', '')))}<br>
Дата доставки: {draft.delivery_date}<br>
Время доставки: {html.escape(str(draft.delivery_time or ''))}<br>
Водитель: {html.escape(str(driver_name))}<br>
Комментарий: {html.escape(draft.comment)}
</div>
<table>
<thead><tr><th>№</th><th>Товар</th><th>Кол-во</th><th>Ед.</th><th>Цена</th><th>Сумма</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<div class="total">Итого: {draft.total_sum:g} ₸</div>
<div class="signatures"><span>Сдал: _____________</span><span>Принял: _____________</span></div>
</body>
</html>'''
        file_path.write_text(content, encoding='utf-8')
        public_link = f'{self.settings.public_base_url}/invoices/{filename}' if self.settings.public_base_url else file_path.resolve().as_uri()
        return InvoiceDocument(invoice_number=invoice_number, file_path=file_path, public_link=public_link)

    @staticmethod
    def build_invoice_number(order: AirtableRecord) -> str:
        order_number = order.get('order_id', order.id[-6:])
        return f'INV-{datetime.now(UTC).strftime("%Y%m%d")}-{order_number}'
