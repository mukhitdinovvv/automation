from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation


from app.config import Settings
from app.models import TIME_WINDOWS


@dataclass(slots=True)
class ParsedItem:
    name: str
    quantity: Decimal


@dataclass(slots=True)
class ParsedOrderText:
    items: list[ParsedItem]
    delivery_date: date | None
    delivery_time: str | None
    comment: str
    needs_confirmation: bool = True


class AssistantService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = None
        if settings.openai_api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    def parse_order_text(self, text: str, today: date) -> ParsedOrderText | None:
        if self.client:
            return self._parse_with_openai(text, today)
        return self._parse_locally(text, today)

    def _parse_with_openai(self, text: str, today: date) -> ParsedOrderText | None:
        prompt = {
            'task': 'Parse Russian/Kazakh food delivery order text into JSON only.',
            'today': today.isoformat(),
            'time_windows': TIME_WINDOWS,
            'schema': {'items': [{'name': 'string', 'quantity': 'number'}], 'delivery_date': 'YYYY-MM-DD or null', 'delivery_time': 'one of time_windows or null', 'comment': 'string'},
            'text': text,
        }
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)}],
            temperature=0,
        )
        content = response.choices[0].message.content or '{}'
        return self._from_json(json.loads(content), today)

    def _parse_locally(self, text: str, today: date) -> ParsedOrderText | None:
        lowered = text.lower()
        delivery_date = today + timedelta(days=1) if 'завтра' in lowered else None
        delivery_time = None
        if 'утром' in lowered or 'утро' in lowered:
            delivery_time = '08:00-10:00'
        elif 'обед' in lowered or 'днем' in lowered or 'днём' in lowered:
            delivery_time = '12:00-14:00'
        elif 'вечер' in lowered:
            delivery_time = '16:00-18:00'
        words = lowered.replace(',', ' ').split()
        items: list[ParsedItem] = []
        for index, word in enumerate(words[:-1]):
            quantity = self._decimal_or_none(word)
            if quantity is not None:
                name = words[index + 1]
                if name not in {'кг', 'шт', 'л', 'упаковка'}:
                    items.append(ParsedItem(name=name, quantity=quantity))
        if not items and 'как обычно' not in lowered:
            return None
        return ParsedOrderText(items=items, delivery_date=delivery_date, delivery_time=delivery_time, comment=text)

    def _from_json(self, payload: dict[str, object], today: date) -> ParsedOrderText | None:
        items: list[ParsedItem] = []
        for raw in payload.get('items', []):
            if isinstance(raw, dict) and raw.get('name'):
                quantity = self._decimal_or_none(str(raw.get('quantity', '')))
                if quantity is not None:
                    items.append(ParsedItem(name=str(raw['name']), quantity=quantity))
        delivery_date = date.fromisoformat(str(payload['delivery_date'])) if payload.get('delivery_date') else None
        if delivery_date and delivery_date < today:
            delivery_date = today
        delivery_time = str(payload.get('delivery_time')) if payload.get('delivery_time') in TIME_WINDOWS else None
        if not items:
            return None
        return ParsedOrderText(items=items, delivery_date=delivery_date, delivery_time=delivery_time, comment=str(payload.get('comment') or ''))

    @staticmethod
    def _decimal_or_none(value: str) -> Decimal | None:
        try:
            return Decimal(value.replace(',', '.'))
        except InvalidOperation:
            return None
