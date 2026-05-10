from __future__ import annotations

from datetime import date, datetime, timedelta

from app.config import Settings


class BusinessRules:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def earliest_delivery_date(self, now: datetime | None = None) -> date:
        current = now or datetime.now(self.settings.tzinfo)
        if current.hour >= self.settings.order_cutoff_hour and self.settings.order_cutoff_hour == 0:
            return (current + timedelta(days=1)).date()
        if current.hour >= self.settings.order_cutoff_hour:
            return (current + timedelta(days=1)).date()
        return current.date()

    def normalize_delivery_date(self, requested: date | None, now: datetime | None = None) -> date:
        earliest = self.earliest_delivery_date(now)
        if requested and requested >= earliest:
            return requested
        return earliest
