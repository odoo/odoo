from psycopg2.extras import Json as PsycopgJson
from xmlrpc.client import MAXINT

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('at_install', '-post_install')
class TestFieldsConversion(TransactionCase):
    def assertStrictlyEqual(self, value, expected):
        self.assertEqual(value, expected)
        self.assertIsInstance(expected, type(value))


@tagged('at_install', '-post_install')
class TestFieldIntegerConversion(TestFieldsConversion):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.record = cls.env['test_orm.fields_conversion'].create([{'name': 'foo'}])
        cls.empty_record = cls.env['test_orm.fields_conversion'].create([])
        cls.company_record = cls.env['test_orm.fields_conversion.company_dependent'].create([{'name': 'foo'}])
        cls.context_record = cls.env['test_orm.fields_conversion.context_dependent'].create([{'name': 'foo'}])

    def test_field_integer_convert_to_write(self):
        # Conversion from any format.
        method = fields.Integer().convert_to_write

        self.assertStrictlyEqual(method(1, self.record), 1)
        self.assertStrictlyEqual(method(1.01, self.record), 1)
        self.assertStrictlyEqual(method(1.99, self.record), 1)
        self.assertStrictlyEqual(method(MAXINT + 1, self.record), MAXINT + 1)
        self.assertStrictlyEqual(method('', self.record), 0)
        self.assertStrictlyEqual(method('1', self.record), 1)
        self.assertStrictlyEqual(method(b'', self.record), 0)
        self.assertStrictlyEqual(method(b'1', self.record), 1)
        self.assertStrictlyEqual(method([], self.record), 0)
        self.assertStrictlyEqual(method({}, self.record), 0)
        self.assertStrictlyEqual(method({'a': 1}, self.record), 0)
        self.assertStrictlyEqual(method({'id': 1}, self.record), 1)
        self.assertStrictlyEqual(method({'id': '1'}, self.record), 1)
        self.assertStrictlyEqual(method(True, self.record), 1)
        self.assertStrictlyEqual(method(False, self.record), 0)
        self.assertStrictlyEqual(method(None, self.record), 0)
        self.assertStrictlyEqual(method(self.empty_record, self.record), 0)
        self.assertStrictlyEqual(method(self.record, self.record), self.record.id)

        with self.assertRaises(ValueError):
            method('a', self.record)

        with self.assertRaises(ValueError):
            method(b'a', self.record)

        with self.assertRaises(TypeError):
            method([1], self.record)

    def test_field_integer_convert_to_column(self):
        # Conversion from write format (int).
        method = fields.Integer().convert_to_column

        self.assertStrictlyEqual(method(1, self.record), 1)

    def test_field_integer_convert_to_column_insert(self):
        # Conversion from write format (int).
        method = fields.Integer().convert_to_column_insert

        self.assertStrictlyEqual(method(1, self.record), 1)

    def test_field_integer_company_dependent_convert_to_column_insert(self):
        # Set up.
        self.env['ir.default'].create({
            'field_id': self.env['ir.model.fields'].search([
                ('model', '=', 'test_orm.fields_conversion.company_dependent'),
                ('name', '=', 'integer')
            ], limit=1).id,
            'json_value': '"1"'
        })

        # Conversion from write format (int).
        method = self.company_record._fields['integer'].convert_to_column_insert

        # Value is fallback.
        self.assertStrictlyEqual(method(1, self.company_record), None)

        # Value is not fallback.
        self.assertEqual(method(2, self.company_record).adapted, PsycopgJson({self.company_record.env.company.id: 2}).adapted)

    def test_field_integer_convert_to_cache(self):
        # Conversions from any format.
        method = fields.Integer().convert_to_cache

        self.assertStrictlyEqual(method(1, self.record), 1)
        self.assertStrictlyEqual(method(1.01, self.record), 1)
        self.assertStrictlyEqual(method(1.99, self.record), 1)
        self.assertStrictlyEqual(method('', self.record), 0)
        self.assertStrictlyEqual(method('1', self.record), 1)
        self.assertStrictlyEqual(method(b'', self.record), 0)
        self.assertStrictlyEqual(method(b'1', self.record), 1)
        self.assertStrictlyEqual(method([], self.record), 0)
        self.assertStrictlyEqual(method({}, self.record), None)
        self.assertStrictlyEqual(method({'a': 1}, self.record), None)
        self.assertStrictlyEqual(method({'id': 1}, self.record), 1)
        self.assertStrictlyEqual(method({'id': '1'}, self.record), 1)
        self.assertStrictlyEqual(method(True, self.record), 1)
        self.assertStrictlyEqual(method(False, self.record), 0)
        self.assertStrictlyEqual(method(None, self.record), 0)
        self.assertStrictlyEqual(method(self.empty_record, self.record), 0)
        self.assertStrictlyEqual(method(self.record, self.record), self.record.id)

        with self.assertRaises(ValueError):
            method('a', self.record)

        with self.assertRaises(ValueError):
            method(b'a', self.record)

        with self.assertRaises(TypeError):
            method([1], self.record)

    def test_field_integer_get_column_update(self):
        # Conversion from cache (int or None).
        method = self.record._fields['integer'].get_column_update

        # Value is not in cache.
        self.env.invalidate_all()

        with self.assertRaises(KeyError):
            method(self.record)

        # Value is in cache.
        self.record.integer = 1
        self.assertStrictlyEqual(method(self.record), 1)

    def test_field_integer_company_dependent_get_column_update(self):
        # Conversion from cache (int or None).
        method = self.company_record._fields['integer'].get_column_update

        # Value is not in cache.
        self.env.invalidate_all()
        self.assertStrictlyEqual(method(self.company_record), None)

        # Value is in cache.
        self.company_record.integer = 2
        self.assertStrictlyEqual(method(self.company_record).adapted, PsycopgJson({self.company_record.env.company.id: 2}).adapted)

    def test_field_integer_context_dependent_get_column_update(self):
        # Conversion from cache (int or None).
        method = self.context_record._fields['integer'].get_column_update

        # Value is not in cache.
        self.env.invalidate_all()

        with self.assertRaises(AssertionError):
            method(self.context_record)

        # Value is in cache and there is only one value: 2.
        self.context_record.name = 'foo'
        self.context_record.with_context(foo=2).integer

        self.assertStrictlyEqual(method(self.context_record), 2)

        # Value is in cache and there is multiple values: 2 and 3.
        self.context_record.name = 'foo'
        self.context_record.with_context(foo=3).integer

        self.assertStrictlyEqual(method(self.context_record), 2)

    def test_field_integer_convert_to_record(self):
        # Conversion from cache format (int or None).
        method = fields.Integer().convert_to_record

        self.assertStrictlyEqual(method(1, self.record), 1)
        self.assertStrictlyEqual(method(None, self.record), 0)

    def test_field_integer_convert_to_read(self):
        # Conversion from record format (int).
        method = fields.Integer().convert_to_read

        self.assertStrictlyEqual(method(1, self.record), 1)
        self.assertStrictlyEqual(method(MAXINT + 1, self.record), float(MAXINT + 1))

    def test_field_integer_convert_to_export(self):
        # Conversion from record format (int).
        method = fields.Integer().convert_to_export

        self.assertStrictlyEqual(method(1, self.record), 1)

    def test_field_integer_convert_to_display_name(self):
        # Conversion from record format (int).
        method = fields.Integer().convert_to_display_name

        self.assertStrictlyEqual(method(1, self.record), '1')
        self.assertStrictlyEqual(method(0, self.record), False)
