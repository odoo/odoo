from odoo import Command
from odoo.addons.account.tests.test_taxes_computation import TestTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationL10nAr(TestTaxesComputation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref('base.ar'))

    def test_21_plus_0_2(self):
        tax_21 = self.percent_tax(21)
        tax_0_2 = self.percent_tax(0.2)
        taxes = tax_21 + tax_0_2

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 7.0, 'price_unit': 124.0, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=1 / 1129.179,
        ))
        expected_base_line_tax_details_values = {
            'raw_total_excluded_currency': 868.0,
            'raw_total_excluded': 980127.372,
            'raw_total_included_currency': 1052.016,
            'raw_total_included': 1187918.89158,
            'total_excluded_currency': 868.0,
            'total_excluded': 980127.37,
            'delta_total_excluded_currency': 0.0,
            'delta_total_excluded': 0.0,
            'total_included_currency': 1052.02,
            'total_included': 1187918.89,
            'taxes_data': [
                {
                    'tax_id': tax_21.id,
                    'raw_base_amount_currency': 868.0,
                    'raw_base_amount': 980127.372,
                    'raw_tax_amount_currency': 182.28,
                    'raw_tax_amount': 205826.74812,
                    'base_amount_currency': 868.0,
                    'base_amount': 980127.37,
                    'tax_amount_currency': 182.28,
                    'tax_amount': 205826.75,
                },
                {
                    'tax_id': tax_0_2.id,
                    'raw_base_amount_currency': 868.0,
                    'raw_base_amount': 980127.372,
                    'raw_tax_amount_currency': 1.736,
                    'raw_tax_amount': 1964.7714600000002,
                    'base_amount_currency': 868.0,
                    'base_amount': 980127.37,
                    'tax_amount_currency': 1.74,
                    'tax_amount': 1964.77,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values],
            expected_base_amount=868.0,
            expected_tax_amount=184.02,
            expected_total_amount=1052.02,
        )

        expected_tax_totals_summary = {
            'base_amount_currency': 868.0,
            'tax_amount_currency': 184.02,
            'total_amount_currency': 1052.02,
        }
        self.assert_tax_totals_summary(document, expected_tax_totals_summary, soft_checking=True)

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 263145.3, 'discount': 25.0, 'tax_ids': tax_21},
            ],
        ))
        expected_base_line_tax_details_values = {
            'raw_total_excluded_currency': 197358.975,
            'raw_total_included_currency': 238804.3608,
            'total_excluded_currency': 197358.98,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 238804.37,
            'taxes_data': [
                {
                    'tax_id': tax_21.id,
                    'raw_base_amount_currency': 197358.975,
                    'raw_tax_amount_currency': 41445.3858,
                    'base_amount_currency': 197358.98,
                    'tax_amount_currency': 41445.39,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values],
            expected_base_amount=197358.98,
            expected_tax_amount=41445.39,
            expected_total_amount=238804.37,
        )

        tax_21.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 263145.3, 'discount': 25.0, 'tax_ids': tax_21},
            ],
        ))
        expected_base_line_tax_details_values = {
            'raw_total_excluded_currency': 163106.595,
            'raw_total_included_currency': 197358.97909090907,
            'total_excluded_currency': 163106.6,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 197358.98,
            'taxes_data': [
                {
                    'tax_id': tax_21.id,
                    'raw_base_amount_currency': 163106.595,
                    'raw_tax_amount_currency': 34252.38409090909,
                    'base_amount_currency': 163106.6,
                    'tax_amount_currency': 34252.38,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values],
            expected_base_amount=163106.6,
            expected_tax_amount=34252.38,
            expected_total_amount=197358.98,
        )

        self._run_js_tests()
