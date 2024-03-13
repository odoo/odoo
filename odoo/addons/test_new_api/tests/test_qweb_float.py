# -*- coding: utf-8 -*-

from odoo.tests import common


class TestFloatExport(common.TransactionCase):

    def get_converter(self, name):
        FloatField = self.env['ir.qweb.field.float']
        _, precision = self.env['decimal.precision.test']._fields[name].get_digits(self.env) or (None, None)

        def converter(value, options=None):
            record = self.env['decimal.precision.test'].new({name: value})
            return FloatField.record_to_html(record, name, options or {})
        return converter

    def test_basic_float(self):
        converter = self.get_converter('float')
        self.assertEqual(
            converter(42.0),
            "42.0")
        self.assertEqual(
            converter(42.12345),
            "42.12345")

        converter = self.get_converter('float_2')
        self.assertEqual(
            converter(42.0),
            "42.00")
        self.assertEqual(
            converter(42.12345),
            "42.12")

        converter = self.get_converter('float') # don't use float_4 because the field value 42.12345 is already orm converted to 42.1235
        self.assertEqual(
            converter(42.0, {'precision': 4}),
            '42.0000')
        self.assertEqual(
            converter(42.12345, {'precision': 4}),
            '42.1235')

    def test_precision_domain(self):
        self.env['decimal.precision'].create({
            'name': 'A',
            'digits': 2,
        })
        self.env['decimal.precision'].create({
            'name': 'B',
            'digits': 6,
        })

        converter = self.get_converter('float')
        self.assertEqual(
            converter(42.0, {'decimal_precision': 'A'}),
            '42.00')
        self.assertEqual(
            converter(42.0, {'decimal_precision': 'B'}),
            '42.000000')

        converter = self.get_converter('float') # don't use float_4 because the field value 42.12345 is orm converted to 42.1235
        self.assertEqual(
            converter(42.12345, {'decimal_precision': 'A'}),
            '42.12')
        self.assertEqual(
            converter(42.12345, {'decimal_precision': 'B'}),
            '42.123450')
