from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesDownPayment(TestTaxCommon):

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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.63,
                'base_amount': 0.13,
                'tax_amount_currency': 0.1,
                'tax_amount': 0.02,
                'total_amount_currency': 0.73,
                'total_amount': 0.15,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.63,
                        'base_amount': 0.13,
                        'tax_amount_currency': 0.1,
                        'tax_amount': 0.02,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 0.14,
                                'tax_amount_currency': 0.02,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 0.14,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 2, expected_values
            yield "round_per_line, price_excluded", document, True, 'fixed', 0.73, expected_values

            # Down Payment 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * percent / 100.0)}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

            # Down Payment 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 2.23,
                'base_amount': 0.43,
                'tax_amount_currency': 0.33,
                'tax_amount': 0.08,
                'total_amount_currency': 2.56,
                'total_amount': 0.51,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 2.23,
                        'base_amount': 0.43,
                        'tax_amount_currency': 0.33,
                        'tax_amount': 0.08,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.45,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.45,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.45,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.45,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2.49,
                                'base_amount': 0.5,
                                'tax_amount_currency': 0.07,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 2.49,
                                'display_base_amount': 0.5,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 7, expected_values
            yield "round_per_line, price_excluded", document, True, 'fixed', 2.56, expected_values

            # Down Payment 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * percent / 100.0)}
                yield "round_per_line, price_excluded", document, True, 'percent', percent, expected_values

            # Down Payment 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 5.73,
                'base_amount': 1.14,
                'tax_amount_currency': 0.87,
                'tax_amount': 0.18,
                'total_amount_currency': 6.6,
                'total_amount': 1.32,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 5.73,
                        'base_amount': 1.14,
                        'tax_amount_currency': 0.87,
                        'tax_amount': 0.18,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 6.4,
                                'base_amount': 1.28,
                                'tax_amount_currency': 0.19,
                                'tax_amount': 0.04,
                                'display_base_amount_currency': 6.4,
                                'display_base_amount': 1.28,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 18, expected_values
            yield "round_per_line, price_excluded", document, True, 'fixed', 6.6, expected_values

            # Down Payment 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * percent / 100.0)}
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.63,
                'base_amount': 0.13,
                'tax_amount_currency': 0.1,
                'tax_amount': 0.02,
                'total_amount_currency': 0.73,
                'total_amount': 0.15,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.63,
                        'base_amount': 0.13,
                        'tax_amount_currency': 0.1,
                        'tax_amount': 0.02,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 0.14,
                                'tax_amount_currency': 0.02,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 0.14,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 2, expected_values
            yield "round_globally, price_excluded", document, True, 'fixed', 0.73, expected_values

            # Down Payment 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * percent / 100.0)}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

            # Down Payment 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 2.24,
                'base_amount': 0.44,
                'tax_amount_currency': 0.33,
                'tax_amount': 0.07,
                'total_amount_currency': 2.57,
                'total_amount': 0.51,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 2.24,
                        'base_amount': 0.44,
                        'tax_amount_currency': 0.33,
                        'tax_amount': 0.07,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.45,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.45,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.45,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.45,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2.49,
                                'base_amount': 0.5,
                                'tax_amount_currency': 0.07,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 2.49,
                                'display_base_amount': 0.5,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 7, expected_values
            yield "round_globally, price_excluded", document, True, 'fixed', 2.57, expected_values

            # Down Payment 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * percent / 100.0)}
                yield "round_globally, price_excluded", document, True, 'percent', percent, expected_values

            # Down Payment 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 5.73,
                'base_amount': 1.14,
                'tax_amount_currency': 0.87,
                'tax_amount': 0.18,
                'total_amount_currency': 6.6,
                'total_amount': 1.32,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 5.73,
                        'base_amount': 1.14,
                        'tax_amount_currency': 0.87,
                        'tax_amount': 0.18,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 6.41,
                                'base_amount': 1.28,
                                'tax_amount_currency': 0.19,
                                'tax_amount': 0.04,
                                'display_base_amount_currency': 6.41,
                                'display_base_amount': 1.28,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 18, expected_values
            yield "round_globally, price_excluded", document, True, 'fixed', 6.6, expected_values

            # Down Payment 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * percent / 100.0)}
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.63,
                'base_amount': 0.13,
                'tax_amount_currency': 0.1,
                'tax_amount': 0.02,
                'total_amount_currency': 0.73,
                'total_amount': 0.15,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.63,
                        'base_amount': 0.13,
                        'tax_amount_currency': 0.1,
                        'tax_amount': 0.02,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 0.14,
                                'tax_amount_currency': 0.02,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 0.14,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 2, expected_values
            yield "round_per_line, price_included", document, True, 'fixed', 0.73, expected_values

            # Down Payment 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * percent / 100.0)}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

            # Down Payment 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 2.23,
                'base_amount': 0.43,
                'tax_amount_currency': 0.33,
                'tax_amount': 0.08,
                'total_amount_currency': 2.56,
                'total_amount': 0.51,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 2.23,
                        'base_amount': 0.43,
                        'tax_amount_currency': 0.33,
                        'tax_amount': 0.08,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.45,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.45,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.45,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.45,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2.49,
                                'base_amount': 0.5,
                                'tax_amount_currency': 0.07,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 2.49,
                                'display_base_amount': 0.5,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 7, expected_values
            yield "round_per_line, price_included", document, True, 'fixed', 2.56, expected_values

            # Down Payment 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * percent / 100.0)}
                yield "round_per_line, price_included", document, True, 'percent', percent, expected_values

            # Down Payment 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 5.73,
                'base_amount': 1.14,
                'tax_amount_currency': 0.87,
                'tax_amount': 0.18,
                'total_amount_currency': 6.6,
                'total_amount': 1.32,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 5.73,
                        'base_amount': 1.14,
                        'tax_amount_currency': 0.87,
                        'tax_amount': 0.18,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 6.4,
                                'base_amount': 1.28,
                                'tax_amount_currency': 0.19,
                                'tax_amount': 0.04,
                                'display_base_amount_currency': 6.4,
                                'display_base_amount': 1.28,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 18, expected_values
            yield "round_per_line, price_included", document, True, 'fixed', 6.6, expected_values

            # Down Payment 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.64 * percent / 100.0)}
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
                                'base_amount_currency': 31.76,
                                'base_amount': 6.35,
                                'tax_amount_currency': 1.91,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.76,
                                'display_base_amount': 6.35,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 31.76,
                                'base_amount': 6.35,
                                'tax_amount_currency': 1.91,
                                'tax_amount': 0.38,
                                'display_base_amount_currency': 31.76,
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.63,
                'base_amount': 0.13,
                'tax_amount_currency': 0.1,
                'tax_amount': 0.02,
                'total_amount_currency': 0.73,
                'total_amount': 0.15,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.63,
                        'base_amount': 0.13,
                        'tax_amount_currency': 0.1,
                        'tax_amount': 0.02,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.64,
                                'base_amount': 0.13,
                                'tax_amount_currency': 0.04,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 0.64,
                                'display_base_amount': 0.13,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 0.14,
                                'tax_amount_currency': 0.02,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 0.14,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 2, expected_values
            yield "round_globally, price_included", document, True, 'fixed', 0.73, expected_values

            # Down Payment 3-6%
            for percent in range(3, 7):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.66 * percent / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

            # Down Payment 7%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 2.24,
                'base_amount': 0.44,
                'tax_amount_currency': 0.33,
                'tax_amount': 0.07,
                'total_amount_currency': 2.57,
                'total_amount': 0.51,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 2.24,
                        'base_amount': 0.44,
                        'tax_amount_currency': 0.33,
                        'tax_amount': 0.07,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.44,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.44,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2.22,
                                'base_amount': 0.44,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.22,
                                'display_base_amount': 0.44,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2.49,
                                'base_amount': 0.5,
                                'tax_amount_currency': 0.07,
                                'tax_amount': 0.01,
                                'display_base_amount_currency': 2.49,
                                'display_base_amount': 0.5,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 7, expected_values

            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 2.23,
                'base_amount': 0.44,
                'tax_amount_currency': 0.34,
                'tax_amount': 0.07,
                'total_amount_currency': 2.57,
                'total_amount': 0.51,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 2.23,
                        'base_amount': 0.44,
                        'tax_amount_currency': 0.34,
                        'tax_amount': 0.07,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2.23,
                                'base_amount': 0.44,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.23,
                                'display_base_amount': 0.44,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2.23,
                                'base_amount': 0.44,
                                'tax_amount_currency': 0.13,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 2.23,
                                'display_base_amount': 0.44,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2.51,
                                'base_amount': 0.5,
                                'tax_amount_currency': 0.07,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 2.51,
                                'display_base_amount': 0.5,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, True, 'fixed', 2.57, expected_values

            # Down Payment 8-17%
            for percent in range(8, 18):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.66 * percent / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

            # Down Payment 18%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 5.73,
                'base_amount': 1.14,
                'tax_amount_currency': 0.87,
                'tax_amount': 0.18,
                'total_amount_currency': 6.6,
                'total_amount': 1.32,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 5.73,
                        'base_amount': 1.14,
                        'tax_amount_currency': 0.87,
                        'tax_amount': 0.18,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 5.72,
                                'base_amount': 1.14,
                                'tax_amount_currency': 0.34,
                                'tax_amount': 0.07,
                                'display_base_amount_currency': 5.72,
                                'display_base_amount': 1.14,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 6.4,
                                'base_amount': 1.28,
                                'tax_amount_currency': 0.19,
                                'tax_amount': 0.04,
                                'display_base_amount_currency': 6.4,
                                'display_base_amount': 1.28,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 18, expected_values
            yield "round_globally, price_included", document, True, 'fixed', 6.6, expected_values

            # Down Payment 19-20%
            for percent in range(19, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(36.67 * percent / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

    def test_taxes_l10n_in_generic_helpers(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_down_payment(document, amount_type, amount, {'tax_totals': expected_values}, soft_checking=soft_checking)
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 1.29,
                'base_amount': 0.43,
                'tax_amount_currency': 0.63,
                'tax_amount': 0.21,
                'total_amount_currency': 1.92,
                'total_amount': 0.64,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 1.29,
                        'base_amount': 0.43,
                        'tax_amount_currency': 0.63,
                        'tax_amount': 0.21,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.1,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.06,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.01,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.17,
                                'tax_amount': 0.06,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.29,
                                'tax_amount': 0.1,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * percent / 100.0)}
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 1.29,
                'base_amount': 0.43,
                'tax_amount_currency': 0.63,
                'tax_amount': 0.21,
                'total_amount_currency': 1.92,
                'total_amount': 0.64,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 1.29,
                        'base_amount': 0.43,
                        'tax_amount_currency': 0.63,
                        'tax_amount': 0.21,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.1,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.06,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.01,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.17,
                                'tax_amount': 0.06,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.29,
                                'tax_amount': 0.1,
                                'display_base_amount_currency': 1.29,
                                'display_base_amount': 0.43,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * percent / 100.0)}
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 1.29,
                'base_amount': 0.43,
                'tax_amount_currency': 0.63,
                'tax_amount': 0.21,
                'total_amount_currency': 1.92,
                'total_amount': 0.64,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 1.29,
                        'base_amount': 0.43,
                        'tax_amount_currency': 0.63,
                        'tax_amount': 0.21,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.1,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.06,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.01,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.17,
                                'tax_amount': 0.06,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.29,
                                'tax_amount': 0.1,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * percent / 100.0)}
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

            # Down Payment 2%
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 1.29,
                'base_amount': 0.43,
                'tax_amount_currency': 0.63,
                'tax_amount': 0.21,
                'total_amount_currency': 1.92,
                'total_amount': 0.64,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 1.29,
                        'base_amount': 0.43,
                        'tax_amount_currency': 0.63,
                        'tax_amount': 0.21,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.1,
                                'tax_amount': 0.03,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.06,
                                'tax_amount': 0.02,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.01,
                                'tax_amount': 0.0,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.17,
                                'tax_amount': 0.06,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 1.29,
                                'base_amount': 0.43,
                                'tax_amount_currency': 0.29,
                                'tax_amount': 0.1,
                                'display_base_amount_currency': 1.92,
                                'display_base_amount': 0.64,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(96.0 * percent / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

    def test_taxes_l10n_br_generic_helpers(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_down_payment(document, amount_type, amount, {'tax_totals': expected_values}, soft_checking=soft_checking)
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
                                'display_base_amount_currency': False,
                                'display_base_amount': False,
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

            # Down payment 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.71,
                'base_amount': 1.42,
                'tax_amount_currency': 0.15,
                'tax_amount': 0.3,
                'total_amount_currency': 0.86,
                'total_amount': 1.72,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.71,
                        'base_amount': 1.42,
                        'tax_amount_currency': 0.15,
                        'tax_amount': 0.3,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 1.42,
                                'tax_amount_currency': 0.15,
                                'tax_amount': 0.3,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 1.42,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_excluded", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.06 * percent / 100.0)}
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
                                'display_base_amount_currency': False,
                                'display_base_amount': False,
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

            # Down payment 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.71,
                'base_amount': 1.42,
                'tax_amount_currency': 0.15,
                'tax_amount': 0.3,
                'total_amount_currency': 0.86,
                'total_amount': 1.72,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.71,
                        'base_amount': 1.42,
                        'tax_amount_currency': 0.15,
                        'tax_amount': 0.3,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 1.42,
                                'tax_amount_currency': 0.15,
                                'tax_amount': 0.3,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 1.42,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_excluded", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.05 * percent / 100.0)}
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
                                'display_base_amount_currency': False,
                                'display_base_amount': False,
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

            # Down payment 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.71,
                'base_amount': 1.42,
                'tax_amount_currency': 0.15,
                'tax_amount': 0.3,
                'total_amount_currency': 0.86,
                'total_amount': 1.72,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.71,
                        'base_amount': 1.42,
                        'tax_amount_currency': 0.15,
                        'tax_amount': 0.3,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 1.42,
                                'tax_amount_currency': 0.15,
                                'tax_amount': 0.3,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 1.42,
                            },
                        ],
                    },
                ],
            }
            yield "round_per_line, price_included", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.06 * percent / 100.0)}
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
                                'display_base_amount_currency': False,
                                'display_base_amount': False,
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

            # Down payment 2%
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 0.71,
                'base_amount': 1.42,
                'tax_amount_currency': 0.15,
                'tax_amount': 0.3,
                'total_amount_currency': 0.86,
                'total_amount': 1.72,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 0.71,
                        'base_amount': 1.42,
                        'tax_amount_currency': 0.15,
                        'tax_amount': 0.3,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 0.71,
                                'base_amount': 1.42,
                                'tax_amount_currency': 0.15,
                                'tax_amount': 0.3,
                                'display_base_amount_currency': 0.71,
                                'display_base_amount': 1.42,
                            },
                        ],
                    },
                ],
            }
            yield "round_globally, price_included", document, False, 'percent', 2, expected_values

            # Down Payment 3-20%
            for percent in range(3, 21):
                expected_values = {'total_amount_currency': self.foreign_currency.round(43.06 * percent / 100.0)}
                yield "round_globally, price_included", document, True, 'percent', percent, expected_values

    def test_taxes_l10n_be_generic_helpers(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_down_payment(document, amount_type, amount, {'tax_totals': expected_values}, soft_checking=soft_checking)
        self._run_js_tests()

    def _test_taxes_fixed_tax_last_position(self):
        tax1 = self.percent_tax(20)
        tax2 = self.fixed_tax(10)
        taxes = tax1 + tax2

        document_params = self.init_document(lines=[{'price_unit': 100.0, 'tax_ids': taxes}])
        document = self.populate_document(document_params)

        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 55.0,
            'tax_amount_currency': 10.0,
            'total_amount_currency': 65.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 55.0,
                    'tax_amount_currency': 10.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 50.0,
                            'tax_amount_currency': 10.0,
                            'display_base_amount_currency': 50.0,
                        },
                    ],
                },
            ],
        }

        yield "include_base_amount=False", document, 'percent', 50.0, expected_values

        tax2.include_base_amount = True
        yield "include_base_amount=True", document, 'percent', 50.0, expected_values

    def test_taxes_fixed_tax_last_position_generic_helpers(self):
        for test_mode, document, amount_type, amount, expected_values in self._test_taxes_fixed_tax_last_position():
            with self.subTest(test_code=test_mode, amount=amount):
                self.assert_down_payment(document, amount_type, amount, {'tax_totals': expected_values})
        self._run_js_tests()

    def _test_no_taxes(self):
        document_params = self.init_document(lines=[
            {'price_unit': 35.0},
            {'price_unit': -5.0},
            {'price_unit': 30.0},
            {'price_unit': 15.0},
            {'price_unit': 15.0},
        ])
        document = self.populate_document(document_params)

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 45.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 45.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 45.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [],
                },
            ],
        }
        return document, 'percent', 50.0, expected_values

    def test_no_taxes_generic_helpers(self):
        document, amount_type, amount, expected_values = self._test_no_taxes()
        self.assert_down_payment(document, amount_type, amount, {'tax_totals': expected_values})
        self._run_js_tests()

    def _test_reverse_charge_tax(self):
        tax = self.percent_tax(
            21,
            invoice_repartition_line_ids=[
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'repartition_type': 'tax'}),
                Command.create({'factor_percent': -100, 'repartition_type': 'tax'}),
            ],
            refund_repartition_line_ids=[
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'repartition_type': 'tax'}),
                Command.create({'factor_percent': -100, 'repartition_type': 'tax'}),
            ],
        )
        document_params = self.init_document(lines=[
            {'price_unit': 12.0, 'tax_ids': tax},
        ])
        document = self.populate_document(document_params)

        expected_tax_totals_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 3.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 3.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 3.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 3.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 3.0,
                        },
                    ],
                },
            ],
        }
        expected_base_line_tax_details_values = [
            {
                'total_excluded': 3.0,
                'total_excluded_currency': 3.0,
                'total_included': 3.0,
                'total_included_currency': 3.0,
                'delta_total_excluded': 0.0,
                'delta_total_excluded_currency': 0.0,
                'manual_total_excluded': 3.0,
                'manual_total_excluded_currency': 3.0,
                'manual_tax_amounts': {
                    str(tax.id): {
                        'tax_amount': 0.63,
                        'tax_amount_currency': 0.63,
                        'base_amount': 3.0,
                        'base_amount_currency': 3.0,
                    },
                },
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'tax_amount': 0.63,
                        'tax_amount_currency': 0.63,
                        'base_amount': 3.0,
                        'base_amount_currency': 3.0,
                    },
                    {
                        'tax_id': tax.id,
                        'tax_amount': -0.63,
                        'tax_amount_currency': -0.63,
                        'base_amount': 3.0,
                        'base_amount_currency': 3.0,
                    },
                ],
            }
        ]
        return document, 'fixed', 3.0, {
            'tax_totals': expected_tax_totals_values,
            'base_lines_tax_details': expected_base_line_tax_details_values,
        }

    def test_reverse_charge_generic_helpers(self):
        document, amount_type, amount, expected_values = self._test_reverse_charge_tax()
        self.assert_down_payment(document, amount_type, amount, expected_values)
        self._run_js_tests()
