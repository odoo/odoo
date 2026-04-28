from odoo import Command
from odoo.addons.account.tests.test_taxes_computation import TestTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationL10nIt(TestTaxesComputation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref('base.it'))

    def test_tax_22(self):
        tax_22 = self.percent_tax(22)

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 100.0335, 'tax_ids': tax_22},
                {'price_unit': 100.0335, 'tax_ids': tax_22},
                {'price_unit': 100.0335, 'tax_ids': tax_22},
            ],
            currency=self.foreign_currency,
            rate=3,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 100.0335,
            'raw_total_excluded': 33.3445,
            'raw_total_included_currency': 122.0435,
            'raw_total_included': 40.68029,
            'total_excluded_currency': 100.03,
            'total_excluded': 33.34,
            'taxes_data': [
                {
                    'tax_id': tax_22.id,
                    'raw_base_amount_currency': 100.0335,
                    'raw_base_amount': 33.3445,
                    'raw_tax_amount_currency': 22.01,
                    'raw_tax_amount': 7.33579,
                    'tax_amount_currency': 22.01,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded': 0.01,
            'delta_total_excluded_currency': 0.01,
            'total_included_currency': 122.05,
            'total_included': 40.69,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 100.04,
                    'base_amount': 33.35,
                    'tax_amount': 7.34,
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded': 0.0,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 122.04,
            'total_included': 40.68,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 100.03,
                    'base_amount': 33.34,
                    'tax_amount': 7.34,
                },
            ],
        }
        expected_base_line_tax_details_values_3 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded': 0.0,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 122.04,
            'total_included': 40.67,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 100.03,
                    'base_amount': 33.34,
                    'tax_amount': 7.33,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
                expected_base_line_tax_details_values_3,
            ],
            expected_base_amount=300.1,
            expected_tax_amount=66.03,
            expected_total_amount=366.13,
        )

        tax_22.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 122.04087, 'tax_ids': tax_22},
                {'price_unit': 122.04087, 'tax_ids': tax_22},
                {'price_unit': 122.04087, 'tax_ids': tax_22},
            ],
            currency=self.foreign_currency,
            rate=3,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 100.03087,
            'raw_total_excluded': 33.3445,
            'raw_total_included_currency': 122.04087,
            'raw_total_included': 40.68029,
            'total_excluded_currency': 100.03,
            'total_excluded': 33.34,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 122.04,
            'taxes_data': [
                {
                    'tax_id': tax_22.id,
                    'raw_base_amount_currency': 100.03087,
                    'raw_base_amount': 33.3445,
                    'raw_tax_amount_currency': 22.01,
                    'raw_tax_amount': 7.33579,
                    'base_amount_currency': 100.03,
                    'tax_amount_currency': 22.01,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded': 0.01,
            'total_included': 40.69,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount': 33.35,
                    'tax_amount': 7.34,
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded': 0.0,
            'total_included': 40.68,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount': 33.34,
                    'tax_amount': 7.34,
                },
            ],
        }
        expected_base_line_tax_details_values_3 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded': 0.0,
            'total_included': 40.67,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount': 33.34,
                    'tax_amount': 7.33,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
                expected_base_line_tax_details_values_3,
            ],
            expected_base_amount=300.09,
            expected_tax_amount=66.03,
            expected_total_amount=366.12,
        )

        self._run_js_tests()
