from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesBaseLinesTaxDetails(TestTaxCommon):
    def test_dispatch_delta_on_base_lines(self):
        """ Make sure that the base line delta is dispatched evenly on base lines.
        Needed for BIS3 rule PEPPOL-EN16931-R120.
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax_21 = self.percent_tax(21.0)
        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 1, 'price_unit': 10.04, 'discount': 10, 'tax_ids': tax_21},
            ] + [
                {'quantity': 1, 'price_unit': 1.04, 'discount': 10, 'tax_ids': tax_21},
            ] * 10,
        ))

        expected_values = {
            'base_lines_tax_details': [
                {
                    'total_excluded': 9.04,
                    'total_excluded_currency': 9.04,
                    'total_included': 10.93,
                    'total_included_currency': 10.93,
                    'delta_total_excluded': -0.01,
                    'delta_total_excluded_currency': -0.01,
                    'taxes_data': [
                        {
                            'tax_id': tax_21.id,
                            'tax_amount': 1.88,
                            'tax_amount_currency': 1.88,
                            'base_amount': 9.02,
                            'base_amount_currency': 9.02,
                        }
                    ],
                },
            ]
            + 2 * [
                {
                    'total_excluded': 0.94,
                    'total_excluded_currency': 0.94,
                    'total_included': 1.13,
                    'total_included_currency': 1.13,
                    'delta_total_excluded': -0.01,
                    'delta_total_excluded_currency': -0.01,
                    'taxes_data': [
                        {
                            'tax_id': tax_21.id,
                            'tax_amount': 0.19,
                            'tax_amount_currency': 0.19,
                            'base_amount': 0.9299999999999999,
                            'base_amount_currency': 0.9299999999999999,
                        }
                    ],
                },
            ]
            + [
                {
                    'total_excluded': 0.94,
                    'total_excluded_currency': 0.94,
                    'total_included': 1.13,
                    'total_included_currency': 1.13,
                    'delta_total_excluded': -0.01,
                    'delta_total_excluded_currency': -0.01,
                    'taxes_data': [
                        {
                            'tax_id': tax_21.id,
                            'tax_amount': 0.2,
                            'tax_amount_currency': 0.2,
                            'base_amount': 0.94,
                            'base_amount_currency': 0.94,
                        }
                    ],
                },
            ]
            + 7 * [
                {
                    'total_excluded': 0.94,
                    'total_excluded_currency': 0.94,
                    'total_included': 1.13,
                    'total_included_currency': 1.13,
                    'delta_total_excluded': 0.0,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_21.id,
                            'tax_amount': 0.2,
                            'tax_amount_currency': 0.2,
                            'base_amount': 0.94,
                            'base_amount_currency': 0.94,
                        }
                    ],
                },
            ],
        }

        self.assert_base_lines_tax_details(document, expected_values)
