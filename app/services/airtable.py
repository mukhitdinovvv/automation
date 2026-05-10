from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from app.config import Settings
from app.models import AirtableRecord


class AirtableError(RuntimeError):
    pass


class AirtableClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = f'https://api.airtable.com/v0/{settings.airtable_base_id}'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {settings.airtable_api_key}',
            'Content-Type': 'application/json',
        })

    def _url(self, table: str, record_id: str | None = None) -> str:
        encoded_table = quote(table, safe='')
        if record_id:
            return f'{self.base_url}/{encoded_table}/{record_id}'
        return f'{self.base_url}/{encoded_table}'

    def _request(self, method: str, table: str, **kwargs: Any) -> dict[str, Any]:
        if not self.settings.airtable_api_key or not self.settings.airtable_base_id:
            raise AirtableError('Airtable credentials are not configured')
        response = self.session.request(method, self._url(table, kwargs.pop('record_id', None)), timeout=30, **kwargs)
        if response.status_code >= 400:
            raise AirtableError(f'Airtable error {response.status_code}: {response.text}')
        return response.json()

    def list_records(self, table: str, formula: str | None = None, max_records: int | None = None, sort: list[dict[str, str]] | None = None) -> list[AirtableRecord]:
        params: dict[str, Any] = {'pageSize': 100}
        if formula:
            params['filterByFormula'] = formula
        if max_records:
            params['maxRecords'] = max_records
        if sort:
            for index, item in enumerate(sort):
                params[f'sort[{index}][field]'] = item['field']
                params[f'sort[{index}][direction]'] = item.get('direction', 'asc')
        records: list[AirtableRecord] = []
        while True:
            payload = self._request('GET', table, params=params)
            records.extend(AirtableRecord(id=item['id'], fields=item.get('fields', {})) for item in payload.get('records', []))
            offset = payload.get('offset')
            if not offset or max_records:
                break
            params['offset'] = offset
        return records

    def get_record(self, table: str, record_id: str) -> AirtableRecord:
        payload = self._request('GET', table, record_id=record_id)
        return AirtableRecord(id=payload['id'], fields=payload.get('fields', {}))

    def create_record(self, table: str, fields: dict[str, Any]) -> AirtableRecord:
        payload = self._request('POST', table, json={'fields': fields})
        return AirtableRecord(id=payload['id'], fields=payload.get('fields', {}))

    def update_record(self, table: str, record_id: str, fields: dict[str, Any]) -> AirtableRecord:
        payload = self._request('PATCH', table, record_id=record_id, json={'fields': fields})
        return AirtableRecord(id=payload['id'], fields=payload.get('fields', {}))


def airtable_string(value: str) -> str:
    return value.replace("'", "\\'")
