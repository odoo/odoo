from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesGlobalDiscount(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')

        cls.tax_groups = cls.env['account.tax.group'].create([
            {'name': str(i), 'sequence': str(i)}
            for i in range(1, 6)
        ])

    def _test_taxes_l10n_in(self):
        """ Test suite for the complex GST taxes in l10n_in. This case implies 3 percentage taxes:
        t1: % tax, include_base_amount
        t2: same % as t1, include_base_amount, not is_base_affected
        t3: % tax

        This case is complex because the amounts of t1 and t2 must always be the same.
        Furthermore, it's a complicated setup due to the usage of include_base_amount / is_base_affected.
        """
        tax1 = self.percent_tax(6, include_base_amount=True, tax_group_id=self.tax_groups[0].id)
        tax2 = self.percent_tax(6, include_base_amount=True, is_base_affected=False, tax_group_id=self.tax_groups[1].id)
        tax3 = self.percent_tax(3, tax_group_id=self.tax_groups[2].id)
        taxes = tax1 + tax2 + tax3

        document_params = self.init_document(
            lines=[
                {'price_unit': 15.89, 'tax_ids': taxes},
                {'price_unit': 15.89, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=5.0,
        )
        with self.with_tax_calculation_rounding_method('round_per_line'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.78,
                'base_amount': 6.36,
                'tax_amount_currency': 4.86,
                'tax_amount': 0.98,
                'total_amount_currency': 36.64,
                'total_amount': 7.34,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.86,
                        'tax_amount': 0.98,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 1.9,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.78,
                                'display_base_amount': 6.36,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 1.9,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.78,
                                'display_base_amount': 6.36,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 35.58,
                                'base_amount': 7.12,
                                'tax_amount_currency': 1.06,
                                'tax_amount': 0.22,
                                'display_base_amount_currency': 35.58,
                                'display_base_amount': 7.12,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.15,
                'base_amount': 6.23,
                'tax_amount_currency': 4.76,
                'tax_amount': 0.96,
                'total_amount_currency': 35.91,
                'total_amount': 7.19,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.15,
                        'base_amount': 6.23,
                        'tax_amount_currency': 4.76,
                        'tax_amount': 0.96,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.15,
                                'base_amount': 6.23,
                                'tax_amount_currency': 1.86,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.15,
                                'display_base_amount': 6.23,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.15,
                                'base_amount': 6.23,
                                'tax_amount_currency': 1.86,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.15,
                                'display_base_amount': 6.23,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 34.87,
                                'base_amount': 6.98,
                                'tax_amount_currency': 1.04,
                                'tax_amount': 0.22,
                                'display_base_amount_currency': 34.87,
                                'display_base_amount': 6.98,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 2, expected_values

            # Discount 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * (100 - percent) / 100.0)}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

            # Discount 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 29.55,
                'base_amount': 5.93,
                'tax_amount_currency': 4.53,
                'tax_amount': 0.9,
                'total_amount_currency': 34.08,
                'total_amount': 6.83,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 29.55,
                        'base_amount': 5.93,
                        'tax_amount_currency': 4.53,
                        'tax_amount': 0.9,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 29.55,
                                'base_amount': 5.93,
                                'tax_amount_currency': 1.77,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.55,
                                'display_base_amount': 5.93,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 29.55,
                                'base_amount': 5.93,
                                'tax_amount_currency': 1.77,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.55,
                                'display_base_amount': 5.93,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 33.09,
                                'base_amount': 6.62,
                                'tax_amount_currency': 0.99,
                                'tax_amount': 0.2,
                                'display_base_amount_currency': 33.09,
                                'display_base_amount': 6.62,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 7, expected_values

            # Discount 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * (100 - percent) / 100.0)}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

            # Discount 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 26.05,
                'base_amount': 5.22,
                'tax_amount_currency': 3.99,
                'tax_amount': 0.8,
                'total_amount_currency': 30.04,
                'total_amount': 6.02,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 26.05,
                        'base_amount': 5.22,
                        'tax_amount_currency': 3.99,
                        'tax_amount': 0.8,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 26.05,
                                'base_amount': 5.22,
                                'tax_amount_currency': 1.56,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.05,
                                'display_base_amount': 5.22,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 26.05,
                                'base_amount': 5.22,
                                'tax_amount_currency': 1.56,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.05,
                                'display_base_amount': 5.22,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 29.17,
                                'base_amount': 5.84,
                                'tax_amount_currency': 0.87,
                                'tax_amount': 0.18,
                                'display_base_amount_currency': 29.17,
                                'display_base_amount': 5.84,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 18, expected_values

            # Discount 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * (100 - percent) / 100.0)}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

        with self.with_tax_calculation_rounding_method('round_globally'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.78,
                'base_amount': 6.36,
                'tax_amount_currency': 4.89,
                'tax_amount': 0.97,
                'total_amount_currency': 36.67,
                'total_amount': 7.33,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.89,
                        'tax_amount': 0.97,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 1.91,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.78,
                                'display_base_amount': 6.36,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 1.91,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.78,
                                'display_base_amount': 6.36,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 35.59,
                                'base_amount': 7.12,
                                'tax_amount_currency': 1.07,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 35.59,
                                'display_base_amount': 7.12,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.15,
                'base_amount': 6.23,
                'tax_amount_currency': 4.79,
                'tax_amount': 0.95,
                'total_amount_currency': 35.94,
                'total_amount': 7.18,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.15,
                        'base_amount': 6.23,
                        'tax_amount_currency': 4.79,
                        'tax_amount': 0.95,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.15,
                                'base_amount': 6.23,
                                'tax_amount_currency': 1.87,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.15,
                                'display_base_amount': 6.23,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.15,
                                'base_amount': 6.23,
                                'tax_amount_currency': 1.87,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.15,
                                'display_base_amount': 6.23,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 34.89,
                                'base_amount': 6.98,
                                'tax_amount_currency': 1.05,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 34.89,
                                'display_base_amount': 6.98,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 2, expected_values

            # Discount 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * (100 - percent) / 100.0)}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

            # Discount 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 29.54,
                'base_amount': 5.92,
                'tax_amount_currency': 4.56,
                'tax_amount': 0.9,
                'total_amount_currency': 34.1,
                'total_amount': 6.82,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 29.54,
                        'base_amount': 5.92,
                        'tax_amount_currency': 4.56,
                        'tax_amount': 0.9,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 29.54,
                                'base_amount': 5.92,
                                'tax_amount_currency': 1.78,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.54,
                                'display_base_amount': 5.92,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 29.54,
                                'base_amount': 5.92,
                                'tax_amount_currency': 1.78,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.54,
                                'display_base_amount': 5.92,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 33.08,
                                'base_amount': 6.62,
                                'tax_amount_currency': 1.0,
                                'tax_amount': 0.20,
                                'display_base_amount_currency': 33.08,
                                'display_base_amount': 6.62,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 7, expected_values

            # Discount 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * (100 - percent) / 100.0)}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

            # Discount 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 26.05,
                'base_amount': 5.22,
                'tax_amount_currency': 4.02,
                'tax_amount': 0.79,
                'total_amount_currency': 30.07,
                'total_amount': 6.01,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 26.05,
                        'base_amount': 5.22,
                        'tax_amount_currency': 4.02,
                        'tax_amount': 0.79,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 26.05,
                                'base_amount': 5.22,
                                'tax_amount_currency': 1.57,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.05,
                                'display_base_amount': 5.22,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 26.05,
                                'base_amount': 5.22,
                                'tax_amount_currency': 1.57,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.05,
                                'display_base_amount': 5.22,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 29.17,
                                'base_amount': 5.84,
                                'tax_amount_currency': 0.88,
                                'tax_amount': 0.17,
                                'display_base_amount_currency': 29.17,
                                'display_base_amount': 5.84,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 18, expected_values

            # Discount 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * (100 - percent) / 100.0)}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

        tax1.price_include_override = 'tax_included'
        tax2.price_include_override = 'tax_included'

        document_params = self.init_document(
            lines=[
                {'price_unit': 17.79, 'tax_ids': taxes},
                {'price_unit': 17.79, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=5.0,
        )
        with self.with_tax_calculation_rounding_method('round_per_line'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.78,
                'base_amount': 6.36,
                'tax_amount_currency': 4.86,
                'tax_amount': 0.98,
                'total_amount_currency': 36.64,
                'total_amount': 7.34,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.86,
                        'tax_amount': 0.98,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 1.9,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.78,
                                'display_base_amount': 6.36,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 1.9,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.78,
                                'display_base_amount': 6.36,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 35.58,
                                'base_amount': 7.12,
                                'tax_amount_currency': 1.06,
                                'tax_amount': 0.22,
                                'display_base_amount_currency': 35.58,
                                'display_base_amount': 7.12,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.15,
                'base_amount': 6.23,
                'tax_amount_currency': 4.76,
                'tax_amount': 0.96,
                'total_amount_currency': 35.91,
                'total_amount': 7.19,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.15,
                        'base_amount': 6.23,
                        'tax_amount_currency': 4.76,
                        'tax_amount': 0.96,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.15,
                                'base_amount': 6.23,
                                'tax_amount_currency': 1.86,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.15,
                                'display_base_amount': 6.23,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.15,
                                'base_amount': 6.23,
                                'tax_amount_currency': 1.86,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.15,
                                'display_base_amount': 6.23,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 34.87,
                                'base_amount': 6.98,
                                'tax_amount_currency': 1.04,
                                'tax_amount': 0.22,
                                'display_base_amount_currency': 34.87,
                                'display_base_amount': 6.98,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 2, expected_values

            # Discount 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * (100 - percent) / 100.0)}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

            # Discount 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 29.55,
                'base_amount': 5.93,
                'tax_amount_currency': 4.53,
                'tax_amount': 0.9,
                'total_amount_currency': 34.08,
                'total_amount': 6.83,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 29.55,
                        'base_amount': 5.93,
                        'tax_amount_currency': 4.53,
                        'tax_amount': 0.9,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 29.55,
                                'base_amount': 5.93,
                                'tax_amount_currency': 1.77,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.55,
                                'display_base_amount': 5.93,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 29.55,
                                'base_amount': 5.93,
                                'tax_amount_currency': 1.77,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.55,
                                'display_base_amount': 5.93,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 33.09,
                                'base_amount': 6.62,
                                'tax_amount_currency': 0.99,
                                'tax_amount': 0.2,
                                'display_base_amount_currency': 33.09,
                                'display_base_amount': 6.62,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 7, expected_values

            # Discount 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * (100 - percent) / 100.0)}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

            # Discount 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 26.05,
                'base_amount': 5.22,
                'tax_amount_currency': 3.99,
                'tax_amount': 0.8,
                'total_amount_currency': 30.04,
                'total_amount': 6.02,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 26.05,
                        'base_amount': 5.22,
                        'tax_amount_currency': 3.99,
                        'tax_amount': 0.8,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 26.05,
                                'base_amount': 5.22,
                                'tax_amount_currency': 1.56,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.05,
                                'display_base_amount': 5.22,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 26.05,
                                'base_amount': 5.22,
                                'tax_amount_currency': 1.56,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.05,
                                'display_base_amount': 5.22,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 29.17,
                                'base_amount': 5.84,
                                'tax_amount_currency': 0.87,
                                'tax_amount': 0.18,
                                'display_base_amount_currency': 29.17,
                                'display_base_amount': 5.84,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 18, expected_values

            # Discount 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * (100 - percent) / 100.0)}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

        with self.with_tax_calculation_rounding_method('round_globally'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.77,
                'base_amount': 6.35,
                'tax_amount_currency': 4.89,
                'tax_amount': 0.97,
                'total_amount_currency': 36.66,
                'total_amount': 7.32,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.77,
                        'base_amount': 6.35,
                        'tax_amount_currency': 4.89,
                        'tax_amount': 0.97,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.77,
                                'base_amount': 6.35,
                                'tax_amount_currency': 1.91,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.77,
                                'display_base_amount': 6.35,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.77,
                                'base_amount': 6.35,
                                'tax_amount_currency': 1.91,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.77,
                                'display_base_amount': 6.35,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 35.58,
                                'base_amount': 7.12,
                                'tax_amount_currency': 1.07,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 35.58,
                                'display_base_amount': 7.12,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 31.14,
                'base_amount': 6.22,
                'tax_amount_currency': 4.79,
                'tax_amount': 0.95,
                'total_amount_currency': 35.93,
                'total_amount': 7.17,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 31.14,
                        'base_amount': 6.22,
                        'tax_amount_currency': 4.79,
                        'tax_amount': 0.95,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 31.14,
                                'base_amount': 6.22,
                                'tax_amount_currency': 1.87,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.14,
                                'display_base_amount': 6.22,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.14,
                                'base_amount': 6.22,
                                'tax_amount_currency': 1.87,
                                'tax_amount': 0.37,
                                'display_base_amount_currency': 31.14,
                                'display_base_amount': 6.22,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 34.88,
                                'base_amount': 6.98,
                                'tax_amount_currency': 1.05,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 34.88,
                                'display_base_amount': 6.98,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 2, expected_values

            # Discount 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.66 * (100 - percent) / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

            # Discount 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 29.53,
                'base_amount': 5.91,
                'tax_amount_currency': 4.56,
                'tax_amount': 0.9,
                'total_amount_currency': 34.09,
                'total_amount': 6.81,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 29.53,
                        'base_amount': 5.91,
                        'tax_amount_currency': 4.56,
                        'tax_amount': 0.9,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 29.53,
                                'base_amount': 5.91,
                                'tax_amount_currency': 1.78,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.53,
                                'display_base_amount': 5.91,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 29.53,
                                'base_amount': 5.91,
                                'tax_amount_currency': 1.78,
                                'tax_amount': 0.35,
                                'display_base_amount_currency': 29.53,
                                'display_base_amount': 5.91,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 33.07,
                                'base_amount': 6.62,
                                'tax_amount_currency': 1.0,
                                'tax_amount': 0.20,
                                'display_base_amount_currency': 33.07,
                                'display_base_amount': 6.62,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 7, expected_values

            # Discount 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.66 * (100 - percent) / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

            # Discount 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 26.04,
                'base_amount': 5.21,
                'tax_amount_currency': 4.02,
                'tax_amount': 0.79,
                'total_amount_currency': 30.06,
                'total_amount': 6.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 26.04,
                        'base_amount': 5.21,
                        'tax_amount_currency': 4.02,
                        'tax_amount': 0.79,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 26.04,
                                'base_amount': 5.21,
                                'tax_amount_currency': 1.57,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.04,
                                'display_base_amount': 5.21,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 26.04,
                                'base_amount': 5.21,
                                'tax_amount_currency': 1.57,
                                'tax_amount': 0.31,
                                'display_base_amount_currency': 26.04,
                                'display_base_amount': 5.21,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 29.17,
                                'base_amount': 5.84,
                                'tax_amount_currency': 0.88,
                                'tax_amount': 0.17,
                                'display_base_amount_currency': 29.17,
                                'display_base_amount': 5.84,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 18, expected_values

            # Discount 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.66 * (100 - percent) / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

    def test_taxes_l10n_in_generic_helpers(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_global_discount(document, amount_type, amount, expected_values, soft_checking=soft_checking)
        self._run_js_tests()

    def _test_taxes_l10n_br(self):
        """ Test suite for the complex division taxes in l10n_be. This case implies 5 division taxes
        and is quite complicated to handle because they have to be computed all together and are
        computed as part of the price_unit.
        """
        tax1 = self.division_tax(5, tax_group_id=self.tax_groups[0].id)
        tax2 = self.division_tax(3, tax_group_id=self.tax_groups[1].id)
        tax3 = self.division_tax(0.65, tax_group_id=self.tax_groups[2].id)
        tax4 = self.division_tax(9, tax_group_id=self.tax_groups[3].id)
        tax5 = self.division_tax(15, tax_group_id=self.tax_groups[4].id)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        document_params = self.init_document(
            lines=[
                {'price_unit': 32.33, 'tax_ids': taxes},
                {'price_unit': 32.33, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        )
        with self.with_tax_calculation_rounding_method('round_per_line'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 64.66,
                'base_amount': 21.56,
                'tax_amount_currency': 31.34,
                'tax_amount': 10.44,
                'total_amount_currency': 96.0,
                'total_amount': 32.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 64.66,
                        'base_amount': 21.56,
                        'tax_amount_currency': 31.34,
                        'tax_amount': 10.44,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 4.8,
                                'tax_amount': 1.6,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.56,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 2.88,
                                'tax_amount': 0.96,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.56,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 0.62,
                                'tax_amount': 0.2,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.56,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 8.64,
                                'tax_amount': 2.88,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.56,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 14.4,
                                'tax_amount': 4.8,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.56,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 63.37,
                'base_amount': 21.13,
                'tax_amount_currency': 30.71,
                'tax_amount': 10.23,
                'total_amount_currency': 94.08,
                'total_amount': 31.36,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 63.37,
                        'base_amount': 21.13,
                        'tax_amount_currency': 30.71,
                        'tax_amount': 10.23,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 4.7,
                                'tax_amount': 1.57,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.13,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 2.82,
                                'tax_amount': 0.94,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.13,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 0.61,
                                'tax_amount': 0.20,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.13,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 8.47,
                                'tax_amount': 2.82,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.13,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 14.11,
                                'tax_amount': 4.7,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.13,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * (100 - percent) / 100.0)}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

        with self.with_tax_calculation_rounding_method('round_globally'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 64.66,
                'base_amount': 21.55,
                'tax_amount_currency': 31.34,
                'tax_amount': 10.45,
                'total_amount_currency': 96.0,
                'total_amount': 32.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 64.66,
                        'base_amount': 21.55,
                        'tax_amount_currency': 31.34,
                        'tax_amount': 10.45,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 4.8,
                                'tax_amount': 1.6,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.55,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 2.88,
                                'tax_amount': 0.96,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.55,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 0.62,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.55,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 8.64,
                                'tax_amount': 2.88,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.55,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 14.4,
                                'tax_amount': 4.8,
                                'display_base_amount_currency': 64.66,
                                'display_base_amount': 21.55,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 63.37,
                'base_amount': 21.12,
                'tax_amount_currency': 30.71,
                'tax_amount': 10.24,
                'total_amount_currency': 94.08,
                'total_amount': 31.36,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 63.37,
                        'base_amount': 21.12,
                        'tax_amount_currency': 30.71,
                        'tax_amount': 10.24,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 4.7,
                                'tax_amount': 1.57,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.12,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 2.82,
                                'tax_amount': 0.94,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.12,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 0.61,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.12,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 8.47,
                                'tax_amount': 2.82,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.12,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 14.11,
                                'tax_amount': 4.7,
                                'display_base_amount_currency': 63.37,
                                'display_base_amount': 21.12,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * (100 - percent) / 100.0)}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

        taxes.price_include_override = 'tax_included'

        document_params = self.init_document(
            lines=[
                {'price_unit': 48.0, 'tax_ids': taxes},
                {'price_unit': 48.0, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        )
        with self.with_tax_calculation_rounding_method('round_per_line'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 64.66,
                'base_amount': 21.56,
                'tax_amount_currency': 31.34,
                'tax_amount': 10.44,
                'total_amount_currency': 96.0,
                'total_amount': 32.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 64.66,
                        'base_amount': 21.56,
                        'tax_amount_currency': 31.34,
                        'tax_amount': 10.44,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 4.8,
                                'tax_amount': 1.6,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 2.88,
                                'tax_amount': 0.96,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 0.62,
                                'tax_amount': 0.2,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 8.64,
                                'tax_amount': 2.88,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.56,
                                'tax_amount_currency': 14.4,
                                'tax_amount': 4.8,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 63.37,
                'base_amount': 21.13,
                'tax_amount_currency': 30.71,
                'tax_amount': 10.23,
                'total_amount_currency': 94.08,
                'total_amount': 31.36,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 63.37,
                        'base_amount': 21.13,
                        'tax_amount_currency': 30.71,
                        'tax_amount': 10.23,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 4.7,
                                'tax_amount': 1.57,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 2.82,
                                'tax_amount': 0.94,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 0.61,
                                'tax_amount': 0.2,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 8.47,
                                'tax_amount': 2.82,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.13,
                                'tax_amount_currency': 14.11,
                                'tax_amount': 4.7,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * (100 - percent) / 100.0)}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

        with self.with_tax_calculation_rounding_method('round_globally'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 64.66,
                'base_amount': 21.55,
                'tax_amount_currency': 31.34,
                'tax_amount': 10.45,
                'total_amount_currency': 96.0,
                'total_amount': 32.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 64.66,
                        'base_amount': 21.55,
                        'tax_amount_currency': 31.34,
                        'tax_amount': 10.45,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 4.8,
                                'tax_amount': 1.6,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 2.88,
                                'tax_amount': 0.96,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 0.62,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 8.64,
                                'tax_amount': 2.88,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 14.4,
                                'tax_amount': 4.8,
                                'display_base_amount_currency': 96.0,
                                'display_base_amount': 32.0,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 63.37,
                'base_amount': 21.12,
                'tax_amount_currency': 30.71,
                'tax_amount': 10.24,
                'total_amount_currency': 94.08,
                'total_amount': 31.36,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 63.37,
                        'base_amount': 21.12,
                        'tax_amount_currency': 30.71,
                        'tax_amount': 10.24,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 4.7,
                                'tax_amount': 1.57,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 2.82,
                                'tax_amount': 0.94,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 0.61,
                                'tax_amount': 0.21,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 8.47,
                                'tax_amount': 2.82,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 63.37,
                                'base_amount': 21.12,
                                'tax_amount_currency': 14.11,
                                'tax_amount': 4.7,
                                'display_base_amount_currency': 94.08,
                                'display_base_amount': 31.36,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * (100 - percent) / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

    def test_taxes_l10n_br_generic_helpers(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_global_discount(document, amount_type, amount, expected_values, soft_checking=soft_checking)
        self._run_js_tests()

    def _test_taxes_l10n_be(self):
        """ Test suite for the mixing of fixed and percentage taxes in l10n_be. This case implies a fixed tax that affect
        the base of the following percentage tax. We also have to maintain the case in which the fixed tax is after the percentage
        one.
        """
        tax1 = self.fixed_tax(1, include_base_amount=True, tax_group_id=self.tax_groups[0].id)
        tax2 = self.percent_tax(21, tax_group_id=self.tax_groups[1].id)
        taxes = tax1 + tax2

        document_params = self.init_document(
            lines=[
                {'price_unit': 16.79, 'tax_ids': taxes},
                {'price_unit': 16.79, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        with self.with_tax_calculation_rounding_method('round_per_line'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 33.58,
                'base_amount': 67.16,
                'tax_amount_currency': 9.48,
                'tax_amount': 18.96,
                'total_amount_currency': 43.06,
                'total_amount': 86.12,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 33.58,
                        'base_amount': 67.16,
                        'tax_amount_currency': 9.48,
                        'tax_amount': 18.96,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 35.58,
                                'base_amount': 71.16,
                                'tax_amount_currency': 7.48,
                                'tax_amount': 14.96,
                                'display_base_amount_currency': 35.58,
                                'display_base_amount': 71.16,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            # The total of the document will be 43.06.
            # However, only the percentage tax is considered in the discount. So the discount will be based on:
            # 2 * 16.79 * 1.21 = 40.6318 ~= 40.63
            # For a discount of 2%,
            # 40.63 * 0.02 = 0.81 is the discount amount.
            # 43.06 - 0.81 = 42.25 is the total amount after discount.
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.91,
                'base_amount': 65.81,
                'tax_amount_currency': 9.34,
                'tax_amount': 18.68,
                'total_amount_currency': 42.25,
                'total_amount': 84.49,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.91,
                        'base_amount': 65.81,
                        'tax_amount_currency': 9.34,
                        'tax_amount': 18.68,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 34.91,
                                'base_amount': 69.81,
                                'tax_amount_currency': 7.34,
                                'tax_amount': 14.68,
                                'display_base_amount_currency': 34.91,
                                'display_base_amount': 69.81,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.06 - (40.64 * percent / 100.0))}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

        with self.with_tax_calculation_rounding_method('round_globally'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 33.58,
                'base_amount': 67.16,
                'tax_amount_currency': 9.47,
                'tax_amount': 18.94,
                'total_amount_currency': 43.05,
                'total_amount': 86.1,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 33.58,
                        'base_amount': 67.16,
                        'tax_amount_currency': 9.47,
                        'tax_amount': 18.94,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 35.58,
                                'base_amount': 71.16,
                                'tax_amount_currency': 7.47,
                                'tax_amount': 14.94,
                                'display_base_amount_currency': 35.58,
                                'display_base_amount': 71.16,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            # The total of the document will be 43.05.
            # However, only the percentage tax is considered in the discount. So the discount will be based on:
            # 2 * 16.79 * 1.21 = 40.6318 ~= 40.63
            # For a discount of 2%,
            # 40.63 * 0.02 = 0.81 is the discount amount.
            # 43.05 - 0.81 = 42.24 is the total amount after discount.
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.91,
                'base_amount': 65.81,
                'tax_amount_currency': 9.33,
                'tax_amount': 18.66,
                'total_amount_currency': 42.24,
                'total_amount': 84.47,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.91,
                        'base_amount': 65.81,
                        'tax_amount_currency': 9.33,
                        'tax_amount': 18.66,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 34.91,
                                'base_amount': 69.81,
                                'tax_amount_currency': 7.33,
                                'tax_amount': 14.66,
                                'display_base_amount_currency': 34.91,
                                'display_base_amount': 69.81,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.05 - (40.63 * percent / 100.0))}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

        taxes.price_include_override = 'tax_included'

        document_params = self.init_document(
            lines=[
                {'price_unit': 21.53, 'tax_ids': taxes},
                {'price_unit': 21.53, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        with self.with_tax_calculation_rounding_method('round_per_line'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 33.58,
                'base_amount': 67.16,
                'tax_amount_currency': 9.48,
                'tax_amount': 18.96,
                'total_amount_currency': 43.06,
                'total_amount': 86.12,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 33.58,
                        'base_amount': 67.16,
                        'tax_amount_currency': 9.48,
                        'tax_amount': 18.96,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 35.58,
                                'base_amount': 71.16,
                                'tax_amount_currency': 7.48,
                                'tax_amount': 14.96,
                                'display_base_amount_currency': 35.58,
                                'display_base_amount': 71.16,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            # The total of the document will be 43.06.
            # However, only the percentage tax is considered in the discount. So the discount will be based on:
            # 2 * 16.79338843 * 1.21 = 40.64
            # For a discount of 2%,
            # 40.64 * 0.02 = 0.81 is the discount amount.
            # 43.06 - 0.81 = 42.25 is the total amount after discount.
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.91,
                'base_amount': 65.81,
                'tax_amount_currency': 9.34,
                'tax_amount': 18.68,
                'total_amount_currency': 42.25,
                'total_amount': 84.49,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.91,
                        'base_amount': 65.81,
                        'tax_amount_currency': 9.34,
                        'tax_amount': 18.68,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 34.91,
                                'base_amount': 69.81,
                                'tax_amount_currency': 7.34,
                                'tax_amount': 14.68,
                                'display_base_amount_currency': 34.91,
                                'display_base_amount': 69.81,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.06 - (40.64 * percent / 100.0))}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

        with self.with_tax_calculation_rounding_method('round_globally'):
            document = self.populate_document(document_params)
            self.assert_py_tax_totals_summary(document, {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 33.59,
                'base_amount': 67.17,
                'tax_amount_currency': 9.47,
                'tax_amount': 18.95,
                'total_amount_currency': 43.06,
                'total_amount': 86.12,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 33.59,
                        'base_amount': 67.17,
                        'tax_amount_currency': 9.47,
                        'tax_amount': 18.95,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.59,
                                'base_amount': 67.17,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 35.59,
                                'base_amount': 71.17,
                                'tax_amount_currency': 7.47,
                                'tax_amount': 14.95,
                                'display_base_amount_currency': 35.59,
                                'display_base_amount': 71.17,
                            },
                        ],
                    },
                ],
            })

            # Discount 2%
            # The total of the document will be 43.06.
            # However, only the percentage tax is considered in the discount. So the discount will be based on:
            # 2 * 16.79338843 * 1.21 = 40.64
            # For a discount of 2%,
            # 40.64 * 0.02 = 0.81 is the discount amount.
            # 43.06 - 0.81 = 42.25 is the total amount after discount.
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.92,
                'base_amount': 65.82,
                'tax_amount_currency': 9.33,
                'tax_amount': 18.67,
                'total_amount_currency': 42.25,
                'total_amount': 84.49,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.92,
                        'base_amount': 65.82,
                        'tax_amount_currency': 9.33,
                        'tax_amount': 18.67,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 33.59,
                                'base_amount': 67.17,
                                'tax_amount_currency': 2.0,
                                'tax_amount': 4.0,
                                'display_base_amount_currency': None,
                                'display_base_amount': None,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 34.92,
                                'base_amount': 69.82,
                                'tax_amount_currency': 7.33,
                                'tax_amount': 14.67,
                                'display_base_amount_currency': 34.92,
                                'display_base_amount': 69.82,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 2, expected_values

            # Discount 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.06 - (40.64 * percent / 100.0))}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

    def test_taxes_l10n_be_generic_helpers(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_global_discount(document, amount_type, amount, expected_values, soft_checking=soft_checking)
        self._run_js_tests()
