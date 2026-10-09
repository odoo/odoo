from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('at_install', '-post_install')
class TestFieldsConversion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.empty_record = cls.env['test_orm.mixed'].create([])
        cls.record = cls.env['test_orm.mixed'].create([{'text': 'hello'}])

    # convert_to_column
    # convert_to_column_insert
    # get_column_update
    # convert_to_cache
    # convert_to_record
    # convert_to_read
    # convert_to_write
    # convert_to_export
    # convert_to_display_name

    def assertStrictlyEqual(self, expected, actual):
        self.assertEqual(expected, actual)
        self.assertIsInstance(actual, type(expected))

    def assertConversion(self, methods, conversions):
        for method in methods:
            for conversion in conversions:
                value = conversion['value']
                expected = conversion['expected']

                if isinstance(expected, Exception):
                    with self.assertRaises(type(expected)):
                        method(value, None)
                else:
                    self.assertStrictlyEqual(expected, method(value, None))

    # ------------------------------------------------------------------------------------------------------------------
    # Binary Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_binary_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Miscellaneous Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_boolean_conversion(self):
        pass

    def test_field_json_conversion(self):
        pass

    def test_field_id_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Numeric Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_integer_conversion(self):
        self.assertConversion([fields.Integer().convert_to_column], [
            {'value': 1,                 'expected': 1},
            {'value': 1.99,              'expected': 1},
            {'value': '',                'expected': 0},
            {'value': '1',               'expected': 1},
            {'value': True,              'expected': 1},
            {'value': False,             'expected': 0},
            {'value': None,              'expected': 0},
            {'value': self.empty_record, 'expected': 0},
            {'value': self.record,       'expected': 1},
            {'value': {'id': 1},         'expected': TypeError()},
        ])

        self.assertConversion([fields.Integer().convert_to_column_insert], [
            {'value': 1,                 'expected': 1},
            {'value': 1.99,              'expected': 1},
            {'value': '',                'expected': 0},
            {'value': '1',               'expected': 1},
            {'value': True,              'expected': 1},
            {'value': False,             'expected': 0},
            {'value': None,              'expected': 0},
            {'value': self.empty_record, 'expected': 0},
            {'value': self.record,       'expected': 1},
            {'value': {'id': 1},         'expected': TypeError()},
        ])

        # get_column_update

        self.assertConversion([fields.Integer().convert_to_cache], [
            {'value': 1,                 'expected': 1},
            {'value': 1.99,              'expected': 1},
            {'value': '',                'expected': 0},
            {'value': '1',               'expected': 1},
            {'value': True,              'expected': 1},
            {'value': False,             'expected': 0},
            {'value': None,              'expected': 0},
            {'value': self.empty_record, 'expected': 0},
            {'value': self.record,       'expected': 1},
            {'value': {'id': 1},         'expected': 1},
        ])

        self.assertConversion([fields.Integer().convert_to_record], [
            {'value': 1,                 'expected': 1},
            {'value': 1.99,              'expected': 1.99},
            {'value': '',                'expected': 0},
            {'value': '1',               'expected': '1'},
            {'value': True,              'expected': True},
            {'value': False,             'expected': 0},
            {'value': None,              'expected': 0},
            {'value': self.empty_record, 'expected': 0},
            {'value': self.record,       'expected': self.record},
            {'value': {'id': 1},         'expected': {'id': 1}},
        ])

        # convert_to_read
        # convert_to_write
        # convert_to_export
        # convert_to_display_name

    def test_field_float_conversion(self):
        pass

    def test_field_monetary_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Properties Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_properties_conversion(self):
        pass

    def test_field_properties_definition_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Reference Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_reference_conversion(self):
        pass

    def test_field_many2one_reference_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Relational Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_many2one_conversion(self):
        pass

    def test_field_one2many_conversion(self):
        pass

    def test_field_many2many_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Selection Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_selection_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Temporal Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_date_conversion(self):
        pass

    def test_field_datetime_conversion(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Textual Fields
    # ------------------------------------------------------------------------------------------------------------------
    def test_field_char_conversion(self):
        pass

    def test_field_text_conversion(self):
        pass

    def test_field_html_conversion(self):
        pass
