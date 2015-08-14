# -*- coding: utf-8 -*-
from openerp.tests import common

class TestFloatExport(common.TransactionCase):
    def setUp(self):
        super(TestFloatExport, self).setUp()
        self.Model = self.registry('decimal.precision.test')

    def get_converter(self, name):
        converter = self.registry('ir.qweb.field.float')
        field = self.Model._fields[name]

        return lambda value, options=None: converter.value_to_html(
            self.cr, self.uid, value, field, options=options, context=None)

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

        converter = self.get_converter('float_4')
        self.assertEqual(
            converter(42.0),
            '42.0000')
        self.assertEqual(
            converter(42.12345),
            '42.1234')

    def test_precision_domain(self):
        DP = self.registry('decimal.precision')
        DP.create(self.cr, self.uid, {
            'name': 'A',
            'digits': 2,
        })
        DP.create(self.cr, self.uid, {
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

        converter = self.get_converter('float_4')
        self.assertEqual(
            converter(42.12345, {'decimal_precision': 'A'}),
            '42.12')
        self.assertEqual(
            converter(42.12345, {'decimal_precision': 'B'}),
            '42.123450')
