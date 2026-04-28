from odoo import Command
from odoo.addons.account.tests.test_taxes_computation import TestTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationL10nKe(TestTaxesComputation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref('base.ke'))

    def test_tax_16(self):
        tax_16 = self.percent_tax(16)

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 100.0335, 'tax_ids': tax_16},
                {'price_unit': 100.0335, 'tax_ids': tax_16},
                {'price_unit': 100.0335, 'tax_ids': tax_16},
            ],
            currency=self.foreign_currency,
            rate=3,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 100.0335,
            'raw_total_excluded': 33.3445,
            'raw_total_included_currency': 116.0235,
            'raw_total_included': 38.6789,
            'total_excluded_currency': 100.03,
            'total_excluded': 33.34,
            'delta_total_excluded': 0.0,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 116.02,
            'total_included': 38.67,
            'taxes_data': [
                {
                    'tax_id': tax_16.id,
                    'raw_base_amount_currency': 100.0335,
                    'raw_base_amount': 33.3445,
                    'raw_tax_amount_currency': 15.99,
                    'raw_tax_amount': 5.3344,
                    'base_amount_currency': 100.03,
                    'base_amount': 33.34,
                    'tax_amount_currency': 15.99,
                    'tax_amount': 5.33,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_common,
                expected_base_line_tax_details_values_common,
                expected_base_line_tax_details_values_common,
            ],
            expected_base_amount=300.09,
            expected_tax_amount=47.97,
            expected_total_amount=348.06,
        )

        tax_16.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 116.0235, 'tax_ids': tax_16},
                {'price_unit': 116.0235, 'tax_ids': tax_16},
                {'price_unit': 116.0235, 'tax_ids': tax_16},
            ],
            currency=self.foreign_currency,
            rate=3,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 100.0335,
            'raw_total_excluded': 33.3445,
            'raw_total_included_currency': 116.0235,
            'raw_total_included': 38.67891379310345,
            'total_excluded_currency': 100.03,
            'total_excluded': 33.34,
            'delta_total_excluded': 0.0,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 116.02,
            'total_included': 38.67,
            'taxes_data': [
                {
                    'tax_id': tax_16.id,
                    'raw_base_amount_currency': 100.0335,
                    'raw_base_amount': 33.3445,
                    'raw_tax_amount_currency': 15.99,
                    'raw_tax_amount': 5.334413793103448,
                    'base_amount_currency': 100.03,
                    'base_amount': 33.34,
                    'tax_amount_currency': 15.99,
                    'tax_amount': 5.33,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_common,
                expected_base_line_tax_details_values_common,
                expected_base_line_tax_details_values_common,
            ],
            expected_base_amount=300.09,
            expected_tax_amount=47.97,
            expected_total_amount=348.06,
        )

        self._run_js_tests()
