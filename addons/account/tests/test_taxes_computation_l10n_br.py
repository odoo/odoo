from odoo import Command
from odoo.addons.account.tests.test_taxes_computation import TestTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationL10nBr(TestTaxesComputation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref('base.br'))

    def test_5_division_taxes(self):
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 32.33, 'tax_ids': taxes},
                {'price_unit': 32.33, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 32.33,
            'raw_total_excluded': 10.776666666666666,
            'raw_total_included_currency': 48.0029695619896,
            'raw_total_included': 16.0,
            'total_excluded_currency': 32.33,
            'total_excluded': 10.78,
            'delta_total_excluded_currency': 0.0,
            'delta_total_excluded': 0.0,
            'total_included_currency': 48.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 2.4001484780994806,
                    'raw_tax_amount': 0.8,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 2.4,
                    'tax_amount': 0.8,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 1.440089086859688,
                    'raw_tax_amount': 0.48,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 1.44,
                    'tax_amount': 0.48,
                },
                {
                    'tax_id': tax3.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 0.31201930215293244,
                    'raw_tax_amount': 0.10333333333333333,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 0.31,
                },
                {
                    'tax_id': tax4.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 4.3202672605790635,
                    'raw_tax_amount': 1.44,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 4.32,
                    'tax_amount': 1.44,
                },
                {
                    'tax_id': tax5.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 7.20044543429844,
                    'raw_tax_amount': 2.4,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 7.2,
                    'tax_amount': 2.4,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'total_included': 16.01,
            'taxes_data': [
                expected_base_line_tax_details_values_common['taxes_data'][0],
                expected_base_line_tax_details_values_common['taxes_data'][1],
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                    'tax_amount': 0.11,
                },
                expected_base_line_tax_details_values_common['taxes_data'][3],
                expected_base_line_tax_details_values_common['taxes_data'][4],
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'total_included': 16.0,
            'taxes_data': [
                expected_base_line_tax_details_values_common['taxes_data'][0],
                expected_base_line_tax_details_values_common['taxes_data'][1],
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                    'tax_amount': 0.1,
                },
                expected_base_line_tax_details_values_common['taxes_data'][3],
                expected_base_line_tax_details_values_common['taxes_data'][4],
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values_1, expected_base_line_tax_details_values_2],
            expected_base_amount=64.66,
            expected_tax_amount=31.34,
            expected_total_amount=96.0,
        )

        # Discount 2%
        expected_base_line_tax_details_global_discount = {
            'raw_total_excluded_currency': -1.2932,
            'raw_total_excluded': -0.43,
            'raw_total_included_currency': -1.9185674832962136,
            'raw_total_included': -0.64,
            'total_excluded_currency': -1.29,
            'total_excluded': -0.43,
            'delta_total_excluded_currency': 0.0,
            'delta_total_excluded': 0.0,
            'total_included_currency': -1.92,
            'total_included': -0.64,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': -1.2932,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.0957683741648107,
                    'raw_tax_amount': -0.03333333333333333,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.1,
                    'tax_amount': -0.03,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': -1.2932,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.0574610244989,
                    'raw_tax_amount': -0.02,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.06,
                    'tax_amount': -0.02,
                },
                {
                    'tax_id': tax3.id,
                    'raw_base_amount_currency': -1.2932,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.01244988864142539,
                    'raw_tax_amount': -0.003333333333333333,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.01,
                    'tax_amount': 0.0,
                },
                {
                    'tax_id': tax4.id,
                    'raw_base_amount_currency': -1.2932,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.17238307349665924,
                    'raw_tax_amount': -0.05666666666666667,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.17,
                    'tax_amount': -0.06,
                },
                {
                    'tax_id': tax5.id,
                    'raw_base_amount_currency': -1.2932,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.2873051224944321,
                    'raw_tax_amount': -0.09666666666666665,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.29,
                    'tax_amount': -0.1,
                },
            ],
        }
        self.assert_global_discount_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=2,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
                expected_base_line_tax_details_global_discount,
            ],
            expected_base_amount=63.37,
            expected_tax_amount=30.71,
            expected_total_amount=94.08,
        )

        # Down Payment 2%
        expected_base_line_tax_details_down_payment = self._reverse_sign(expected_base_line_tax_details_global_discount)
        self.assert_down_payment_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=2,
            expected_base_lines_tax_details=[expected_base_line_tax_details_down_payment],
            expected_base_amount=1.29,
            expected_tax_amount=0.63,
            expected_total_amount=1.92,
        )

        taxes.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 48.0, 'tax_ids': taxes},
                {'price_unit': 48.0, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        ))
        expected_base_line_tax_details_values_common = {
            'raw_total_excluded_currency': 32.33,
            'raw_total_excluded': 10.776666666666666,
            'raw_total_included_currency': 48.002,
            'raw_total_included': 16.0,
            'total_excluded_currency': 32.33,
            'total_excluded': 10.78,
            'delta_total_excluded': 0.0,
            'delta_total_excluded_currency': 0.0,
            'total_included_currency': 48.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 2.40,
                    'raw_tax_amount': 0.8,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 2.4,
                    'tax_amount': 0.8,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 1.44,
                    'raw_tax_amount': 0.48,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 1.44,
                    'tax_amount': 0.48,
                },
                {
                    'tax_id': tax3.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 0.312,
                    'raw_tax_amount': 0.10333333333333333,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 0.31,
                },
                {
                    'tax_id': tax4.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 4.32,
                    'raw_tax_amount': 1.44,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 4.32,
                    'tax_amount': 1.44,
                },
                {
                    'tax_id': tax5.id,
                    'raw_base_amount_currency': 32.33,
                    'raw_base_amount': 10.776666666666666,
                    'raw_tax_amount_currency': 7.2,
                    'raw_tax_amount': 2.4,
                    'base_amount_currency': 32.33,
                    'base_amount': 10.78,
                    'tax_amount_currency': 7.2,
                    'tax_amount': 2.4,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'total_included': 16.01,
            'taxes_data': [
                expected_base_line_tax_details_values_common['taxes_data'][0],
                expected_base_line_tax_details_values_common['taxes_data'][1],
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                    'tax_amount': 0.11,
                },
                expected_base_line_tax_details_values_common['taxes_data'][3],
                expected_base_line_tax_details_values_common['taxes_data'][4],
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'total_included': 16.0,
            'taxes_data': [
                expected_base_line_tax_details_values_common['taxes_data'][0],
                expected_base_line_tax_details_values_common['taxes_data'][1],
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                    'tax_amount': 0.1,
                },
                expected_base_line_tax_details_values_common['taxes_data'][3],
                expected_base_line_tax_details_values_common['taxes_data'][4],
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values_1, expected_base_line_tax_details_values_2],
            expected_base_amount=64.66,
            expected_tax_amount=31.34,
            expected_total_amount=96.0,
        )

        # Discount 2%
        expected_base_line_tax_details_global_discount = {
            'raw_total_excluded_currency': -1.29,
            'raw_total_excluded': -0.43,
            'raw_total_included_currency': -1.91688,
            'raw_total_included': -0.64,
            'total_excluded_currency': -1.29,
            'total_excluded': -0.43,
            'delta_total_excluded_currency': 0.0,
            'delta_total_excluded': 0.0,
            'total_included_currency': -1.92,
            'total_included': -0.64,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': -1.29,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.096,
                    'raw_tax_amount': -0.03333333333333333,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.1,
                    'tax_amount': -0.03,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': -1.29,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.0576,
                    'raw_tax_amount': -0.02,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.06,
                    'tax_amount': -0.02,
                },
                {
                    'tax_id': tax3.id,
                    'raw_base_amount_currency': -1.29,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.01248,
                    'raw_tax_amount': -0.003333333333333333,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.01,
                    'tax_amount': 0.0,
                },
                {
                    'tax_id': tax4.id,
                    'raw_base_amount_currency': -1.29,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.1728,
                    'raw_tax_amount': -0.05666666666666667,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.17,
                    'tax_amount': -0.06,
                },
                {
                    'tax_id': tax5.id,
                    'raw_base_amount_currency': -1.29,
                    'raw_base_amount': -0.43,
                    'raw_tax_amount_currency': -0.288,
                    'raw_tax_amount': -0.09666666666666665,
                    'base_amount_currency': -1.29,
                    'base_amount': -0.43,
                    'tax_amount_currency': -0.29,
                    'tax_amount': -0.1,
                },
            ],
        }
        self.assert_global_discount_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=2,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
                expected_base_line_tax_details_global_discount,
            ],
            expected_base_amount=63.37,
            expected_tax_amount=30.71,
            expected_total_amount=94.08,
        )

        self._run_js_tests()
