from contextlib import contextmanager

from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesTaxTotalsSummary(TestTaxCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')
        cls.tax_groups = cls.env['account.tax.group'].create([
            {'name': str(i), 'sequence': str(i)}
            for i in range(1, 10)
        ])

    @contextmanager
    def same_tax_group(self, taxes):
        taxes.tax_group_id = self.tax_groups[0]
        yield

    @contextmanager
    def different_tax_group(self, taxes):
        for i, tax in enumerate(taxes):
            tax.tax_group_id = self.tax_groups[i]
        yield

    def test_reverse_charge_taxes_1(self):
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax}],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 100.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_reverse_charge_taxes_2(self):
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 11178.65, 'discount': 10.0, 'tax_ids': tax}],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 10060.79,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 10060.79,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 10060.79,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 10060.79,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 10060.79,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_random_case_tax_included(self):
        tax = self.percent_tax(20.0, price_include_override='tax_included')
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 24.99, 'tax_ids': tax}],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 20.82,
            'tax_amount_currency': 4.17,
            'total_amount_currency': 24.99,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 20.82,
                    'tax_amount_currency': 4.17,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 20.82,
                            'tax_amount_currency': 4.17,
                            'display_base_amount_currency': 20.82,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)

        tax_1 = self.percent_tax(10.0, price_include_override='tax_included', tax_group_id=self.tax_groups[0].id)
        tax_2 = self.percent_tax(10.0, price_include_override='tax_included', tax_group_id=self.tax_groups[1].id)
        taxes = tax_1 + tax_2
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 24.99, 'tax_ids': tax}],
        ))
        self.assert_tax_totals_summary(document, expected_values)

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 100.0, 'tax_ids': taxes},
                {'price_unit': -90.0, 'tax_ids': taxes},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 8.34,
            'tax_amount_currency': 1.66,
            'total_amount_currency': 10.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 8.34,
                    'tax_amount_currency': 1.66,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 8.34,
                            'tax_amount_currency': 0.83,
                            'display_base_amount_currency': 8.34,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 8.34,
                            'tax_amount_currency': 0.83,
                            'display_base_amount_currency': 8.34,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_cash_rounding(self):
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        with self.same_tax_group(taxes):
            cash_rounding = self.env['account.cash.rounding'].create({
                'name': 'add_invoice_line',
                'rounding': 0.05,
                'strategy': 'add_invoice_line',
                'profit_account_id': self.company_data['default_account_revenue'].id,
                'loss_account_id': self.company_data['default_account_expense'].id,
                'rounding_method': 'HALF-UP',
            })

            document = self.populate_document(self.init_document(
                lines=[{'price_unit': 32.4, 'tax_ids': taxes}],
                currency=self.foreign_currency,
                rate=0.5,
                cash_rounding=cash_rounding,
            ))

            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.4,
                'base_amount': 64.8,
                'cash_rounding_base_amount_currency': -0.01,
                'cash_rounding_base_amount': -0.02,
                'tax_amount_currency': 15.71,
                'tax_amount': 31.42,
                'total_amount_currency': 48.1,
                'total_amount': 96.2,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.4,
                        'base_amount': 64.8,
                        'tax_amount_currency': 15.71,
                        'tax_amount': 31.42,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 15.71,
                                'tax_amount': 31.42,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                        ],
                    },
                ],
            }
            self.assert_tax_totals_summary(document, expected_values)

        with self.different_tax_group(taxes):
            cash_rounding = self.env['account.cash.rounding'].create({
                'name': 'biggest_tax',
                'rounding': 0.05,
                'strategy': 'biggest_tax',
                'rounding_method': 'HALF-UP',
            })

            document = self.populate_document(self.init_document(
                lines=[{'price_unit': 32.4, 'tax_ids': taxes}],
                currency=self.foreign_currency,
                rate=0.5,
                cash_rounding=cash_rounding,
            ))

            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.40,
                'base_amount': 64.8,
                'tax_amount_currency': 15.7,
                'tax_amount': 31.40,
                'total_amount_currency': 48.10,
                'total_amount': 96.2,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.40,
                        'base_amount': 64.8,
                        'tax_amount_currency': 15.7,
                        'tax_amount': 31.40,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 2.41,
                                'tax_amount': 4.82,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 1.44,
                                'tax_amount': 2.88,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 0.31,
                                'tax_amount': 0.62,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 4.33,
                                'tax_amount': 8.66,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 7.21,
                                'tax_amount': 14.42,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                        ],
                    },
                ],
            }
            self.assert_tax_totals_summary(document, expected_values)

            document = self.populate_document(self.init_document(
                lines=[{'price_unit': 50.01}],
                cash_rounding=cash_rounding,
            ))
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 50.01,
                'tax_amount_currency': 0.0,
                'total_amount_currency': 50.01,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 50.01,
                        'tax_amount_currency': 0.0,
                        'tax_groups': [],
                    },
                ],
            }
            self.assert_tax_totals_summary(document, expected_values)

        self._run_js_tests()

    def test_cash_rounding_with_excluded_tax_groups(self):
        # Excluded tax groups are not managed js-side nor on invoices. However, they are used
        # in some localizations to build another tax totals aside.
        tax1 = self.division_tax(5, tax_group_id=self.tax_groups[0].id)
        tax2 = self.division_tax(3, tax_group_id=self.tax_groups[1].id)
        tax3 = self.division_tax(0.65, tax_group_id=self.tax_groups[2].id)
        tax4 = self.division_tax(9, tax_group_id=self.tax_groups[3].id)
        tax5 = self.division_tax(15, tax_group_id=self.tax_groups[4].id)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        cash_rounding = self.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })

        document_params = self.init_document(
            lines=[{'price_unit': 32.4, 'tax_ids': taxes}],
            currency=self.foreign_currency,
            rate=0.5,
            cash_rounding=cash_rounding,
        )
        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 44.25,
            'base_amount': 88.5,
            'tax_amount_currency': 3.85,
            'tax_amount': 7.7,
            'total_amount_currency': 48.10,
            'total_amount': 96.20,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 44.25,
                    'base_amount': 88.5,
                    'tax_amount_currency': 3.85,
                    'tax_amount': 7.7,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 32.4,
                            'base_amount': 64.8,
                            'tax_amount_currency': 2.41,
                            'tax_amount': 4.82,
                            'display_base_amount_currency': 32.4,
                            'display_base_amount': 64.8,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 32.4,
                            'base_amount': 64.8,
                            'tax_amount_currency': 1.44,
                            'tax_amount': 2.88,
                            'display_base_amount_currency': 32.4,
                            'display_base_amount': 64.8,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values, excluded_tax_group_ids=self.tax_groups[2:5].ids)

    def test_mixed_combined_standalone_taxes(self):
        tax_10 = self.percent_tax(10.0)
        tax_10_incl_base = self.percent_tax(10.0, include_base_amount=True)
        tax_20 = self.percent_tax(20.0)
        taxes = tax_10 + tax_20 + tax_10_incl_base

        document1 = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 1000.0, 'tax_ids': tax_10 + tax_20},
                {'price_unit': 1000.0, 'tax_ids': tax_10},
                {'price_unit': 1000.0, 'tax_ids': tax_20},
            ],
        ))
        document2 = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 1000.0, 'tax_ids': tax_10_incl_base + tax_20},
                {'price_unit': 1000.0, 'tax_ids': tax_10_incl_base},
                {'price_unit': 1000.0, 'tax_ids': tax_20},
            ],
        ))

        with self.same_tax_group(taxes):
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 600.0,
                'total_amount_currency': 3600.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 600.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 3000.0,
                                'tax_amount_currency': 600.0,
                                'display_base_amount_currency': 3000.0,
                            },
                        ],
                    },
                ],
            }
            self.assert_tax_totals_summary(document1, expected_values)

            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 620.0,
                'total_amount_currency': 3620.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 620.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 3000.0,
                                'tax_amount_currency': 620.0,
                                'display_base_amount_currency': 3000.0,
                            },
                        ],
                    },
                ],
            }
            self.assert_tax_totals_summary(document2, expected_values)

        with self.different_tax_group(taxes):
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 600.0,
                'total_amount_currency': 3600.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 600.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2000.0,
                                'tax_amount_currency': 200.0,
                                'display_base_amount_currency': 2000.0,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2000.0,
                                'tax_amount_currency': 400.0,
                                'display_base_amount_currency': 2000.0,
                            },
                        ],
                    },
                ],
            }
            self.assert_tax_totals_summary(document1, expected_values)

            expected_values = {
                'same_tax_base': False,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 620.0,
                'total_amount_currency': 3620.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 620.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2100.0,
                                'tax_amount_currency': 420.0,
                                'display_base_amount_currency': 2100.0,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2000.0,
                                'tax_amount_currency': 200.0,
                                'display_base_amount_currency': 2000.0,
                            },
                        ],
                    },
                ],
            }
            self.assert_tax_totals_summary(document2, expected_values)
        self._run_js_tests()

    def test_preceding_subtotal(self):
        self.tax_groups[1].preceding_subtotal = "PRE GROUP 1"
        self.tax_groups[2].preceding_subtotal = "PRE GROUP 2"
        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[1].id)
        tax_25 = self.percent_tax(25.0, tax_group_id=self.tax_groups[2].id)
        tax_42 = self.percent_tax(42.0, tax_group_id=self.tax_groups[0].id)

        document = self.populate_document(self.init_document([
            {'price_unit': 1000.0},
            {'price_unit': 1000.0, 'tax_ids': tax_10},
            {'price_unit': 1000.0, 'tax_ids': tax_25},
            {'price_unit': 100.0, 'tax_ids': tax_42},
            {'price_unit': 200.0, 'tax_ids': tax_42 + tax_10 + tax_25},
        ]))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 3300.0,
            'tax_amount_currency': 546.0,
            'total_amount_currency': 3846.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 3300.0,
                    'tax_amount_currency': 126.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 300.0,
                            'tax_amount_currency': 126.0,
                            'display_base_amount_currency': 300.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 1",
                    'base_amount_currency': 3426.0,
                    'tax_amount_currency': 120.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 1200.0,
                            'tax_amount_currency': 120.0,
                            'display_base_amount_currency': 1200.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 2",
                    'base_amount_currency': 3546.0,
                    'tax_amount_currency': 300.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 1200.0,
                            'tax_amount_currency': 300.0,
                            'display_base_amount_currency': 1200.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)

        self.tax_groups[3].preceding_subtotal = "PRE GROUP 1"  # same as tax_groups[1], on purpose
        tax_10.tax_group_id = self.tax_groups[3]  # preceding_subtotal == "PRE GROUP 1"
        tax_42.tax_group_id = self.tax_groups[1]  # preceding_subtotal == "PRE GROUP 1"
        tax_minus_25 = self.percent_tax(-25.0, tax_group_id=self.tax_groups[2].id)  # preceding_subtotal == "PRE GROUP 2"
        tax_30 = self.percent_tax(30.0, tax_group_id=self.tax_groups[0].id)

        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax_10},
            {'price_unit': 100.0, 'tax_ids': tax_minus_25 + tax_42 + tax_30},
            {'price_unit': 200.0, 'tax_ids': tax_10 + tax_minus_25},
            {'price_unit': 1000.0, 'tax_ids': tax_30},
            {'price_unit': 100.0, 'tax_ids': tax_30 + tax_10},
        ]))

        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 1500.0,
            'tax_amount_currency': 367.0,
            'total_amount_currency': 1867.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1500.0,
                    'tax_amount_currency': 360.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 1200.0,
                            'tax_amount_currency': 360.0,
                            'display_base_amount_currency': 1200.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 1",
                    'base_amount_currency': 1860.0,
                    'tax_amount_currency': 82.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 42.0,
                            'display_base_amount_currency': 100.0,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 400.0,
                            'tax_amount_currency': 40.0,
                            'display_base_amount_currency': 400.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 2",
                    'base_amount_currency': 1942.0,
                    'tax_amount_currency': -75.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 300.0,
                            'tax_amount_currency': -75.0,
                            'display_base_amount_currency': 300.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_preceding_subtotal_with_tax_group(self):
        self.tax_groups[1].preceding_subtotal = "Tax withholding"
        tax_minus_47 = self.percent_tax(-47.0, tax_group_id=self.tax_groups[1].id)
        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[0].id)
        tax_group = self.group_of_taxes(tax_minus_47 + tax_10)

        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax_group},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': -37.0,
            'total_amount_currency': 63.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 10.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 10.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
                {
                    'name': "Tax withholding",
                    'base_amount_currency': 110.0,
                    'tax_amount_currency': -47.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': -47.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_preceding_subtotal_with_include_base_amount(self):
        self.tax_groups[1].preceding_subtotal = "PRE GROUP 1"
        self.tax_groups[2].preceding_subtotal = "PRE GROUP 2"
        tax_1 = self.percent_tax(10.0, include_base_amount=True, tax_group_id=self.tax_groups[1].id)
        tax_2 = self.percent_tax(20.0, include_base_amount=True, tax_group_id=self.tax_groups[1].id)
        tax_3 = self.percent_tax(30.0, include_base_amount=True, tax_group_id=self.tax_groups[1].id)
        tax_4 = self.percent_tax(50.0, tax_group_id=self.tax_groups[2].id)

        document = self.populate_document(self.init_document([
            {'price_unit': 1000.0, 'tax_ids': tax_1 + tax_2 + tax_3 + tax_4},
        ]))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 1000.0,
            'tax_amount_currency': 1574.0,
            'total_amount_currency': 2574.0,
            'subtotals': [
                {
                    'name': "PRE GROUP 1",
                    'base_amount_currency': 1000.0,
                    'tax_amount_currency': 716.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 1000.0,
                            'tax_amount_currency': 716.0,
                            'display_base_amount_currency': 1000.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 2",
                    'base_amount_currency': 1716.0,
                    'tax_amount_currency': 858.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 1716.0,
                            'tax_amount_currency': 858.0,
                            'display_base_amount_currency': 1716.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_reverse_charge_percent_tax(self):
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )

        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 100.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)

        tax.price_include_override = 'tax_included'
        document = self.populate_document(self.init_document([
            {'price_unit': 121.0, 'tax_ids': tax},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 121.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 121.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 121.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 121.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 121.0,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()


    def test_discount_with_round_globally(self):
        tax = self.percent_tax(21.0)

        document_params = self.init_document([
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
        ])

        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 141.48,
            'tax_amount_currency': 29.71,
            'total_amount_currency': 171.19,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 141.48,
                    'tax_amount_currency': 29.71,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 141.48,
                            'tax_amount_currency': 29.71,
                            'display_base_amount_currency': 141.48,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)

        tax.price_include_override = 'tax_included'

        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 116.93,
            'tax_amount_currency': 24.55,
            'total_amount_currency': 141.48,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 116.93,
                    'tax_amount_currency': 24.55,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 116.93,
                            'tax_amount_currency': 24.55,
                            'display_base_amount_currency': 116.93,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_archived_tax_in_tax_totals(self):
        tax_10 = self.percent_tax(15.0)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2020-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_10.ids)],
                })
            ],
        })

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 15.0,
            'total_amount_currency': 115.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 15.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 15.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values)
        tax_10.active = False
        invoice.env.invalidate_all()
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values)

    def test_price_included_taxes_with_0_price_excluded_tax(self):
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')
        tax_6 = self.percent_tax(6.0, price_include_override='tax_included')
        tax_0 = self.percent_tax(0.0, price_include_override='tax_excluded')

        document_params = self.init_document([
            {'price_unit': 27.80, 'tax_ids': tax_21},
            {'price_unit': 97.25, 'tax_ids': tax_6},
            {'price_unit': 9.0, 'tax_ids': tax_0},
        ])

        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 123.73,
            'tax_amount_currency': 10.32,
            'total_amount_currency': 134.05,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 123.73,
                    'tax_amount_currency': 10.32,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 123.73,
                            'tax_amount_currency': 10.32,
                            'display_base_amount_currency': 123.73,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()
