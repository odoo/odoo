from odoo import Command
from odoo.addons.account.tests.test_taxes_computation import TestTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationL10nMx(TestTaxesComputation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref('base.mx'))

    def test_8_ieps_plus_16_plus_10_67_withholding(self):
        tax_8_ieps = self.percent_tax(8.0, include_base_amount=True)
        tax_16 = self.percent_tax(16.0)
        tax_10_67_wh = self.percent_tax(-10.67)
        taxes = tax_8_ieps + tax_16 + tax_10_67_wh

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 15.794, 'tax_ids': taxes},
                {'price_unit': 15.794, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=2,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 15.794,
            'raw_total_excluded': 7.8975,
            'raw_total_included_currency': 17.966686,
            'raw_total_included': 8.985,
            'total_excluded_currency': 15.79,
            'total_excluded': 7.9,
            'delta_total_excluded': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax_8_ieps.id,
                    'raw_base_amount_currency': 15.794,
                    'raw_base_amount': 7.8975,
                    'raw_tax_amount_currency': 1.26352,
                    'raw_tax_amount': 0.6325,
                    'base_amount': 7.9,
                },
                {
                    'tax_id': tax_16.id,
                    'raw_base_amount_currency': 17.05752,
                    'raw_base_amount': 8.53,
                    'raw_tax_amount_currency': 2.729203,
                    'raw_tax_amount': 1.365,
                    'base_amount_currency': 17.06,
                    'base_amount': 8.53,
                    'tax_amount_currency': 2.73,
                },
                {
                    'tax_id': tax_10_67_wh.id,
                    'raw_base_amount_currency': 17.05752,
                    'raw_base_amount': 8.53,
                    'raw_tax_amount_currency': -1.820037,
                    'raw_tax_amount': -0.91,
                    'base_amount_currency': 17.06,
                    'base_amount': 8.53,
                    'tax_amount_currency': -1.82,
                    'tax_amount': -0.91,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded_currency': 0.01,
            'total_included_currency': 17.98,
            'total_included': 9.0,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 15.80,
                    'tax_amount_currency': 1.27,
                    'tax_amount': 0.64,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][1],
                    'tax_amount': 1.37,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 17.96,
            'total_included': 8.98,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 15.79,
                    'tax_amount_currency': 1.26,
                    'tax_amount': 0.63,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][1],
                    'tax_amount': 1.36,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values_1, expected_base_line_tax_details_values_2],
            expected_base_amount=31.59,
            expected_tax_amount=4.35,
            expected_total_amount=35.94,
        )

        taxes.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 17.967, 'tax_ids': taxes},
                {'price_unit': 17.967, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=2,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 15.794276,
            'raw_total_excluded': 7.8975,
            'raw_total_included_currency': 17.967,
            'raw_total_included': 8.985,
            'total_excluded_currency': 15.79,
            'total_excluded': 7.9,
            'delta_total_excluded': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax_8_ieps.id,
                    'raw_base_amount_currency': 15.794276,
                    'raw_base_amount': 7.8975,
                    'raw_tax_amount_currency': 1.263542,
                    'raw_tax_amount': 0.6325,
                    'base_amount': 7.9,
                },
                {
                    'tax_id': tax_16.id,
                    'raw_base_amount_currency': 17.057818,
                    'raw_base_amount': 8.53,
                    'raw_tax_amount_currency': 2.729251,
                    'raw_tax_amount': 1.365,
                    'base_amount_currency': 17.06,
                    'base_amount': 8.53,
                    'tax_amount_currency': 2.73,
                },
                {
                    'tax_id': tax_10_67_wh.id,
                    'raw_base_amount_currency': 17.057818,
                    'raw_base_amount': 8.53,
                    'raw_tax_amount_currency': -1.820069,
                    'raw_tax_amount': -0.91,
                    'base_amount_currency': 17.06,
                    'base_amount': 8.53,
                    'tax_amount_currency': -1.82,
                    'tax_amount': -0.91,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded_currency': 0.01,
            'total_included_currency': 17.98,
            'total_included': 9.0,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 15.80,
                    'tax_amount_currency': 1.27,
                    'tax_amount': 0.64,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][1],
                    'tax_amount': 1.37,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 17.96,
            'total_included': 8.98,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 15.79,
                    'tax_amount_currency': 1.26,
                    'tax_amount': 0.63,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][1],
                    'tax_amount': 1.36,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values_1, expected_base_line_tax_details_values_2],
            expected_base_amount=31.59,
            expected_tax_amount=4.35,
            expected_total_amount=35.94,
        )

        self._run_js_tests()
