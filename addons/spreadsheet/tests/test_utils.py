import datetime

from odoo.tests.common import TransactionCase

from odoo.addons.spreadsheet.utils.formatting import (
    date_to_spreadsheet_date_number,
    datetime_to_spreadsheet_date_number,
)
from odoo.addons.spreadsheet.utils.json import extend_serialized_json


class TestSpreadsheetUtils(TransactionCase):

    def test_extend_serialized_json(self):
        self.assertEqual(extend_serialized_json('{}', []), '{}')
        self.assertEqual(extend_serialized_json('{}', [('key', '{}')]), '{"key":{}}')
        self.assertEqual(extend_serialized_json('{}', [('key', '[]')]), '{"key":[]}')
        self.assertEqual(
            extend_serialized_json('{}', [('key', '"value"')]),
            '{"key":"value"}'
        )
        self.assertEqual(
            extend_serialized_json('{"a": 1}', [('key', '"value"')]),
            '{"a": 1,"key":"value"}'
        )
        self.assertEqual(
            extend_serialized_json('{"a": 1}', [('key', '{"b": 2}')]),
            '{"a": 1,"key":{"b": 2}}'
        )
        self.assertEqual(
            extend_serialized_json('{"a": {}}', [('key', '{"b": 2}')]),
            '{"a": {},"key":{"b": 2}}'
        )
        self.assertEqual(
            extend_serialized_json('{"a": 1}', [('key', '[]')]),
            '{"a": 1,"key":[]}'
        )
        self.assertEqual(
            extend_serialized_json('{"a": []}', [('key', '[]')]),
            '{"a": [],"key":[]}'
        )
        self.assertEqual(
            extend_serialized_json('{}', [('key1', '1'), ('key2', '2')]),
            '{"key1":1,"key2":2}'
        )

    def test_date_to_spreadsheet_date_number(self):
        d = datetime.date(1899, 12, 30)
        self.assertEqual(date_to_spreadsheet_date_number(d), 0)

        d = datetime.date(2023, 10, 1)
        self.assertEqual(date_to_spreadsheet_date_number(d), 45200)

    def test_datetime_to_spreadsheet_date_number(self):
        test_tz_offset = 8 / 24  # Etc/GMT-8 is UTC+8
        dt = datetime.datetime(1899, 12, 30, 0, 0, 0)
        self.assertEqual(datetime_to_spreadsheet_date_number(dt, 'UTC'), 0)

        dt = datetime.datetime(1899, 12, 30, 0, 0, 0)
        self.assertEqual(datetime_to_spreadsheet_date_number(dt, 'Etc/GMT-8'), test_tz_offset)

        dt = datetime.datetime(2023, 10, 1, 12, 0, 0)
        self.assertEqual(datetime_to_spreadsheet_date_number(dt, 'UTC'), 45200.5)

        dt = datetime.datetime(2023, 10, 1, 12, 0, 0)
        self.assertEqual(datetime_to_spreadsheet_date_number(dt, 'Etc/GMT-8'), 45200.5 + test_tz_offset)
