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
    def test_field_integer_convert_to_write(self):
        # Set up.
        empty_record = self.env['test_orm.fields_conversion'].create([])
        record = self.env['test_orm.fields_conversion'].create([{'name': 'foo'}])

        # Conversion from any format.
        method = fields.Integer().convert_to_write

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method(1.01, None), 1)
        self.assertStrictlyEqual(method(1.99, None), 1)
        self.assertStrictlyEqual(method(MAXINT + 1, None), float(MAXINT + 1))  # FIX ME: it should be an int
        self.assertStrictlyEqual(method('', None), 0)
        self.assertStrictlyEqual(method('1', None), 1)
        self.assertStrictlyEqual(method(b'', None), 0)
        self.assertStrictlyEqual(method(b'1', None), 1)
        self.assertStrictlyEqual(method([], None), 0)
        self.assertStrictlyEqual(method({}, None), 0)
        self.assertStrictlyEqual(method({'a': 1}, None), 0)
        self.assertStrictlyEqual(method({'id': 1}, None), 1)
        self.assertStrictlyEqual(method(True, None), 1)
        self.assertStrictlyEqual(method(False, None), 0)
        self.assertStrictlyEqual(method(None, None), 0)
        self.assertStrictlyEqual(method(empty_record, None), 0)
        self.assertStrictlyEqual(method(record, None), record.id)

        with self.assertRaises(ValueError): method('a', None)
        with self.assertRaises(ValueError): method(b'a', None)

        with self.assertRaises(TypeError): method([1], None)
        with self.assertRaises(TypeError): method({'id': '1'}, None)

    def test_field_integer_convert_to_column(self):
        # Conversion from write format.
        method = fields.Integer().convert_to_column

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method(float(MAXINT + 1), None), MAXINT + 1)

    def test_field_integer_convert_to_column_insert(self):
        # Conversion from write format.
        method = fields.Integer().convert_to_column_insert

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method(float(MAXINT + 1), None), MAXINT + 1)

    def test_field_integer_convert_to_cache(self):
        # Set up.
        empty_record = self.env['test_orm.fields_conversion'].create([])
        record = self.env['test_orm.fields_conversion'].create([{'name': 'foo'}])

        # Conversions from any format.
        method = fields.Integer().convert_to_cache

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method(1.01, None), 1)
        self.assertStrictlyEqual(method(1.99, None), 1)
        self.assertStrictlyEqual(method('', None), 0)
        self.assertStrictlyEqual(method('1', None), 1)
        self.assertStrictlyEqual(method(b'', None), 0)
        self.assertStrictlyEqual(method(b'1', None), 1)
        self.assertStrictlyEqual(method([], None), 0)
        self.assertStrictlyEqual(method({}, None), None)
        self.assertStrictlyEqual(method({'a': 1}, None), None)
        self.assertStrictlyEqual(method({'id': 1}, None), 1)
        self.assertStrictlyEqual(method({'id': '1'}, None), '1')  # FIX ME: it should return 1
        self.assertStrictlyEqual(method(True, None), 1)
        self.assertStrictlyEqual(method(False, None), 0)
        self.assertStrictlyEqual(method(None, None), 0)
        self.assertStrictlyEqual(method(empty_record, None), 0)
        self.assertStrictlyEqual(method(record, None), record.id)

        with self.assertRaises(ValueError): method('a', None)
        with self.assertRaises(ValueError): method(b'a', None)

        with self.assertRaises(TypeError): method([1], None)

    def test_field_integer_get_column_update(self):
        # Set up.
        record = self.env['test_orm.fields_conversion'].create([{'name': 'foo'}])

        # Conversion from cache.
        method = record._fields['integer'].get_column_update

        # Value is not in cache.
        self.env.invalidate_all()
        with self.assertRaises(KeyError): method(record)

        # Value is in cache.
        record.integer = 1
        self.assertStrictlyEqual(method(record), 1)

    def test_field_integer_convert_to_record(self):
        # Conversion from cache format.
        method = fields.Integer().convert_to_record

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method('1', None), '1')  # FIX ME: convert_to_cache() should return 1
        self.assertStrictlyEqual(method(None, None), 0)

    def test_field_integer_convert_to_read(self):
        # Conversion from record format.
        method = fields.Integer().convert_to_read

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method(MAXINT + 1, None), float(MAXINT + 1))

        with self.assertRaises(TypeError): method('1', None)  # FIX ME: convert_to_cache() should return 1

    def test_field_integer_convert_to_export(self):
        # Conversion from record format.
        method = fields.Integer().convert_to_export

        self.assertStrictlyEqual(method(1, None), 1)
        self.assertStrictlyEqual(method('1', None), '1')  # FIX ME: convert_to_cache() should return 1

    def test_field_integer_convert_to_display_name(self):
        # Conversion from record format.
        method = fields.Integer().convert_to_display_name

        self.assertStrictlyEqual(method(1, None), '1')
        self.assertStrictlyEqual(method(0, None), False)

    def test_field_integer_company_dependent_convert_to_column_insert(self):
        # Set up.
        record = self.env['test_orm.fields_conversion.company_dependent'].create([{'name': 'foo'}])

        self.env['ir.default'].create({
            'field_id': self.env['ir.model.fields'].search([
                ('model', '=', 'test_orm.fields_conversion.company_dependent'),
                ('name', '=', 'integer')
            ], limit=1).id,
            'json_value': '"1"'
        })

        # Conversion from write format.
        method = record._fields['integer'].convert_to_column_insert

        # Value is fallback.
        self.assertStrictlyEqual(method(1, record), None)

        # Value is not fallback.
        self.assertEqual(method(2, record).adapted, PsycopgJson({record.env.company.id: 2}).adapted)

    def test_field_integer_company_dependent_get_column_update(self):
        # Set up.
        record = self.env['test_orm.fields_conversion.company_dependent'].create([{'name': 'foo'}])

        # Conversion from cache.
        method = record._fields['integer'].get_column_update

        # Value is not in cache.
        self.env.invalidate_all()
        self.assertStrictlyEqual(method(record), None)

        # Value is in cache.
        record.integer = 2
        self.assertStrictlyEqual(method(record).adapted, PsycopgJson({record.env.company.id: 2}).adapted)

    def test_field_integer_context_dependent_get_column_update(self):
        # Set up.
        record = self.env['test_orm.fields_conversion.context_dependent'].create([{'name': 'foo'}])

        # Conversion from cache.
        method = record._fields['integer'].get_column_update

        # Value is not in cache.
        self.env.invalidate_all()
        with self.assertRaises(AssertionError): method(record)

        # Value is in cache and there is only one value: 2.
        record.name = 'foo'
        record.with_context(foo=2).integer

        self.assertStrictlyEqual(method(record), 2)

        # Value is in cache and there is multiple values: 2 and 3.
        record.name = 'foo'
        record.with_context(foo=3).integer

        self.assertStrictlyEqual(method(record), 2)
