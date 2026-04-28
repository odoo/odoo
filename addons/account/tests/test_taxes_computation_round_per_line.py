from odoo import Command
from odoo.addons.account.tests.test_taxes_computation import TestTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationRoundPerLine(TestTaxesComputation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.tax_calculation_rounding_method = 'round_per_line'

    def test_taxes_price_excluded(self):
        tax_21 = self.percent_tax(21)

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 16.794, 'tax_ids': tax_21},
                {'price_unit': 16.794, 'tax_ids': tax_21},
            ],
            currency=self.foreign_currency,
            rate=2,
        ))
        expected_base_line_tax_details_values = {
            'raw_total_excluded_currency': 16.794,
            'raw_total_excluded': 8.395,
            'raw_total_included_currency': 20.3199,
            'raw_total_included': 10.16,
            'total_excluded_currency': 16.79,
            'total_excluded': 8.4,
            'delta_total_excluded_currency': 0.0,
            'delta_total_excluded': 0.0,
            'total_included_currency': 20.32,
            'total_included': 10.17,
            'taxes_data': [
                {
                    'tax_id': tax_21.id,
                    'raw_base_amount_currency': 16.794,
                    'raw_base_amount': 8.395,
                    'raw_tax_amount_currency': 3.5259,
                    'raw_tax_amount': 1.765,
                    'base_amount_currency': 16.79,
                    'base_amount': 8.4,
                    'tax_amount_currency': 3.53,
                    'tax_amount': 1.77,
                }
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values, expected_base_line_tax_details_values],
            expected_base_amount=33.58,
            expected_tax_amount=7.06,
            expected_total_amount=40.64,
        )

        self._run_js_tests()

    def test_taxes_price_included(self):
        tax_21 = self.percent_tax(21, price_include_override='tax_included')

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 20.321, 'tax_ids': tax_21},
                {'price_unit': 20.321, 'tax_ids': tax_21},
            ],
            currency=self.foreign_currency,
            rate=2,
        ))
        expected_base_line_tax_details_values = {
            'raw_total_excluded_currency': 16.791,
            'raw_total_excluded': 8.395,
            'total_excluded_currency': 16.79,
            'total_excluded': 8.4,
            'delta_total_excluded_currency': 0.0,
            'delta_total_excluded': 0.0,
            'raw_total_included_currency': 20.317785123966942,
            'raw_total_included': 10.16,
            'total_included_currency': 20.32,
            'total_included': 10.17,
            'taxes_data': [
                {
                    'tax_id': tax_21.id,
                    'raw_base_amount_currency': 16.791,
                    'raw_base_amount': 8.395,
                    'raw_tax_amount_currency': 3.526785124,
                    'raw_tax_amount': 1.765,
                    'base_amount_currency': 16.79,
                    'base_amount': 8.40,
                    'tax_amount_currency': 3.53,
                    'tax_amount': 1.77,
                }
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values, expected_base_line_tax_details_values],
            expected_base_amount=33.58,
            expected_tax_amount=7.06,
            expected_total_amount=40.64,
        )

        self._run_js_tests()
