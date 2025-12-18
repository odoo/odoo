from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesBaseLinesTaxDetails(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.tax_calculation_rounding_method = 'round_globally'

    def test_dispatch_delta_on_base_lines(self):
        """ Make sure that the base line delta is dispatched evenly on base lines.
        Needed for BIS3 rule PEPPOL-EN16931-R120.
        """
        tax_21 = self.percent_tax(21.0)
        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 10.04, 'discount': 10, 'tax_ids': tax_21},
            ] + [
                {'price_unit': 1.04, 'discount': 10, 'tax_ids': tax_21},
            ] * 10,
        ))

        line_1_expected_values = {
            'total_excluded': 9.04,
            'total_excluded_currency': 9.04,
            'total_included': 10.94,
            'total_included_currency': 10.94,
            'delta_total_excluded': 0.0,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax_21.id,
                    'tax_amount': 1.8699999999999999,
                    'tax_amount_currency': 1.8699999999999999,
                    'base_amount': 9.01,
                    'base_amount_currency': 9.01,
                }
            ],
        }
        line_2_expected_values = {
            'total_excluded': 0.94,
            'total_excluded_currency': 0.94,
            'total_included': 1.14,
            'total_included_currency': 1.14,
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
        }

        expected_values = {
            'base_lines_tax_details': [
                {
                    **line_1_expected_values,
                    'delta_total_excluded': -0.03,
                    'delta_total_excluded_currency': -0.03,
                },
                {
                    **line_2_expected_values,
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
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
                line_2_expected_values,
            ]
        }

        self.assert_base_lines_tax_details(document, expected_values)

    def test_dispatch_delta_on_net_zero_tax(self):
        """Check that the base line delta still is dispatched if net tax is zero."""
        def get_expected_values(base_values, tax):
            expected_tax_total = sum(values[2] for values in base_expected_values)
            self.assertTrue(
                tax.company_id.currency_id.is_zero(expected_tax_total),
                "Expected taxes should add up to zero.",
            )
            return {
                'base_lines_tax_details': [{
                    'delta_total_excluded': 0.0,
                    'delta_total_excluded_currency': 0.0,
                    'total_excluded': total_excluded,
                    'total_excluded_currency': total_excluded,
                    'total_included': total_included,
                    'total_included_currency': total_included,
                    'taxes_data': [{
                        'base_amount': total_excluded,
                        'base_amount_currency': total_excluded,
                        'tax_amount': tax_amount,
                        'tax_amount_currency': tax_amount,
                        'tax_id': tax.id,
                    }],
                } for total_excluded, total_included, tax_amount in base_values],
            }

        with self.subTest("19.99% tax, 100% global discount"):
            tax_19_99 = self.percent_tax(19.99)
            lines_vals = [{
                'price_unit': price,
                'quantity': 1,
                'tax_ids': tax_19_99,
            } for price in (19.99, 19.99, -39.98)]
            document = self.populate_document(self.init_document(lines_vals))

            base_expected_values = [
            #   (total_excluded, total_included, tax_amount),
                (19.99, 23.99, 4.0),
                (19.99, 23.99, 4.0),
                (-39.98, -47.97, -8.0),
            ]
            expected_values = get_expected_values(base_expected_values, tax_19_99)
            self.assert_base_lines_tax_details(document, expected_values)

        with self.subTest("7% tax, 30% line discount, 100% global discount"):
            tax_7 = self.percent_tax(7.0)
            lines_vals = [{
                'price_unit': price,
                'quantity': 4,
                'discount': 30,
                'tax_ids': tax_7,
            } for price in (1068, 46, 46, 298, 5)]
            lines_vals.append({'price_unit': -4096.4, 'tax_ids': tax_7})  # 100% discount
            document = self.populate_document(self.init_document(lines_vals))

            base_expected_values = [
            #   (total_excluded, total_included, tax_amount),
                (2990.4, 3199.73, 209.33),
                (128.8, 137.82000000000002, 9.02),
                (128.8, 137.82000000000002, 9.02),
                (834.4, 892.81, 58.41),
                (14.0, 14.98, 0.98),
                (-4096.4, -4383.15, -286.76),
            ]
            expected_values = get_expected_values(base_expected_values, tax_7)
            self.assert_base_lines_tax_details(document, expected_values)
