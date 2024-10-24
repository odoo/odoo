from odoo.tests.common import TransactionCase

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
