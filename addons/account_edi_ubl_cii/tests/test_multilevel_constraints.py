from odoo.tests import tagged
from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestMultilevelConstraints(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None

        cls.simple_data = {
            'ubl20_supplier_name_required': "The field 'name' is required on 'res.partner'.",
            'ubl20_invoice_name_required': "The field 'name' is required on 'account.invoice'.",
        }

        cls.complex_data = {
            '_ignored_key': 1,
            'oth_err_1': "Some random error",
            'oth_err_2': "Some other random error",
            'ubl_20': {
                '_title': "UBL 2.0 Errors",
                'ubl20_supplier_name_required': "The field 'name' is required on 'res.partner'.",
                'ubl20_invoice_name_required': "The field 'name' is required on 'account.invoice'.",
            },
            'other_err_3': "Something is wrong",
            "important": {
                '_title': "Important Errors",
                'general_important_error': "This is a general important error",
                'some_subtitle': {
                    '_title': "Some Subtitle",
                    'error_1': "Something is wrong with the thing",
                },
                'some_other_subtitle': {
                    '_title': "Some Other Subtitle",
                    'error_2': "Something is wrong with the other thing",
                },
            },
            'empty': {
                '_title': "Empty constraints dict",
            },
        }

    def test_nop(self):
        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(self.simple_data)
        self.assertDictEqual(self.simple_data, flattened)

    def test_empty_nested_constraints(self):
        data = self.simple_data.copy()
        data['empty_nested_constraints'] = {
            '_title': "Empty Nested Constraints",
        }

        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(data)
        self.assertDictEqual(self.simple_data, flattened)

    def test_empty_deep_nested_constraints(self):
        data = self.simple_data.copy()
        data['empty_nested_constraints'] = {
            '_title': "Empty Nested Constraints",
            'deep_nested_constraints_1': {
                '_title': "Deep Nested Constraints 1",
            },
            'deep_nested_constraints_2': {
                '_title': "Deep Nested Constraints 2",
            },
        }

        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(data)
        self.assertDictEqual(self.simple_data, flattened)

    def test_only_residuals(self):
        data = {
            'general_error': "General error",
            'other': {
                'my_other': "My other error",
            },
        }

        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(data)
        expected = {
            'my_other': "My other error",
            'general_error': "General error",
        }

        self.assertDictEqual(expected, flattened)

    def test_custom_key(self):
        data = {
            '_config': {
                'residual_key': 'custom_residual_key',
            },
            'other': {
                '_title': "Nested Constraints",
                'con_1': "Some random error",
            }
        }

        expected = {
            'other': "Nested Constraints\n\tSome random error",
        }

        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(data)
        self.assertDictEqual(expected, flattened)

    def test_complex_constraints(self):
        self.complex_data['_config'] = {
            'residual_title': "Custom title for residual errors",
        }

        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(self.complex_data)
        expected = {
            'ubl_20': "UBL 2.0 Errors\n\tThe field 'name' is required on 'res.partner'.\n\tThe field 'name' is required on 'account.invoice'.",
            'important': "Important Errors\n\tThis is a general important error\n\tSome Subtitle\n\t\tSomething is wrong with the thing\n\tSome Other Subtitle\n\t\tSomething is wrong with the other thing",
            'other': "Custom title for residual errors\n\tSome random error\n\tSome other random error\n\tSomething is wrong",
        }
        self.assertDictEqual(expected, flattened)

    def test_custom_config(self):
        self.complex_data['_config'] = {
            'residual_title': "Custom title for residual errors",
            'residual_key': "custom_key",
            'indent_suffix': '- ',
        }

        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(self.complex_data)
        expected = {
            'ubl_20': "- UBL 2.0 Errors\n\t- The field 'name' is required on 'res.partner'.\n\t- The field 'name' is required on 'account.invoice'.",
            'important': "- Important Errors\n\t- This is a general important error\n\t- Some Subtitle\n\t\t- Something is wrong with the thing\n\t- Some Other Subtitle\n\t\t- Something is wrong with the other thing",
            'custom_key': "- Custom title for residual errors\n\t- Some random error\n\t- Some other random error\n\t- Something is wrong",
        }
        self.assertDictEqual(expected, flattened)

        self.complex_data['_config']['indent_suffix_on_root_titles'] = False
        expected = {k: v[2:] for k, v in expected.items()}
        flattened = self.env['account.edi.common']._flatten_multilevel_constraints(self.complex_data)
        self.assertDictEqual(expected, flattened)
