# -*- coding: utf-8 -*-
# pylint: disable=C0326
from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged, HttpCase, Form


@tagged('post_install', '-at_install')
class TestDeferredReports(TestAccountReportsCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.deferred_expense_report = cls.env.ref('account_reports.deferred_expense_report')
        cls.deferred_revenue_report = cls.env.ref('account_reports.deferred_revenue_report')
        cls.handler = cls.env['account.deferred.expense.report.handler']

        cls.expense_accounts = [cls.env['account.account'].create({
            'name': f'Expense {i}',
            'code': f'EXP{i}',
            'account_type': 'expense',
        }) for i in range(10)]
        cls.revenue_accounts = [cls.env['account.account'].create({
            'name': f'Revenue {i}',
            'code': f'REV{i}',
            'account_type': 'income',
        }) for i in range(3)]

        cls.company = cls.company_data['company']
        cls.deferral_account = cls.company_data['default_account_deferred_expense']
        cls.company.deferred_expense_journal_id = cls.company_data['default_journal_misc'].id
        cls.company.deferred_revenue_journal_id = cls.company_data['default_journal_misc'].id
        cls.company.deferred_expense_account_id = cls.company_data['default_account_deferred_expense'].id
        cls.company.deferred_revenue_account_id = cls.company_data['default_account_deferred_revenue'].id

        cls.expense_lines = [
            [cls.expense_accounts[0], 1000, '2023-01-01', '2023-04-30'],  # 4 full months (=250/month)
            [cls.expense_accounts[0], 1050, '2023-01-16', '2023-04-30'],  # 3 full months + 15 days (=300/month)
            [cls.expense_accounts[1], 1225, '2023-01-01', '2023-04-15'],  # 3 full months + 15 days (=350/month)
            [cls.expense_accounts[2], 1680, '2023-01-21', '2023-04-14'],  # 2 full months + 10 days + 14 days (=600/month)
            [cls.expense_accounts[2],  225, '2023-04-01', '2023-04-15'],  # 15 days (=450/month)
        ]
        cls.revenue_lines = [
            [cls.revenue_accounts[0], 1000, '2023-01-01', '2023-04-30'],  # 4 full months (=250/month)
            [cls.revenue_accounts[0], 1050, '2023-01-16', '2023-04-30'],  # 3 full months + 15 days (=300/month)
            [cls.revenue_accounts[1], 1225, '2023-01-01', '2023-04-15'],  # 3 full months + 15 days (=350/month)
            [cls.revenue_accounts[2], 1680, '2023-01-21', '2023-04-14'],  # 2 full months + 10 days + 14 days (=600/month)
            [cls.revenue_accounts[2],  225, '2023-04-01', '2023-04-15'],  # 15 days (=450/month)
        ]

    def create_invoice(self, invoice_lines, move_type='in_invoice', invoice_date='2023-01-01', post=True):
        journal = self.company_data['default_journal_sale']
        if move_type.startswith('in_'):
            journal = self.company_data['default_journal_purchase']
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'date': invoice_date,
            'invoice_date': invoice_date,
            'journal_id': journal.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'account_id': invoice_line[0].id,
                    'price_unit': invoice_line[1],
                    'deferred_start_date': invoice_line[2],
                    'deferred_end_date': invoice_line[3],
                }) for invoice_line in invoice_lines
            ]
        })
        if post:
            move.action_post()
        return move

    def get_options(self, from_date, to_date, report=None):
        report = report or self.deferred_expense_report
        return self._generate_options(report, from_date, to_date)

    def get_lines(self, options, report=None):
        report = report if report is not None else self.deferred_expense_report
        # Clear the cache to avoid any interference with the previous test
        # This is automatically done when clicking on a report,
        # but it needs to be manually done here since we call the backend function directly
        self.env.cr.cache.pop('report_deferred_lines', None)
        return report._get_lines(options)

    def generate_deferral_entries(self, options, report_handler=None):
        report_handler = report_handler if report_handler is not None else self.handler
        self.env.cr.cache.pop('report_deferred_lines', None)  # same as above
        return report_handler._generate_deferral_entry(options)

    def test_deferred_expense_report_months(self):
        """
        Test the deferred expense report with the 'month' method.
        We use multiple report months/quarters/years to check that the computation is correct.
        """
        self.company.deferred_expense_amount_computation_method = 'month'
        self.create_invoice(self.expense_lines)

        # December 2022
        options = self.get_options('2022-12-01', '2022-12-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # January 2023
        options = self.get_options('2023-01-01', '2023-01-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before   Current              Later
            [    0,                  1,             2,            3,       4,                   5                       ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            0,       250 + 150,           750 + 900               ),
                ('EXP1 Expense 1',   1225,          0,            0,       350,                 875                     ),
                ('EXP2 Expense 2',   1680 + 225,    225,          0,       600 * (10/30) + 0,   600 * (2 + 14/30) + 225 ),
                ('Total',            5180,          225,          0,       950,                 4230                    ),
            ],
            options,
        )

        # February 2023
        options = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before               Current      Later
            [    0,                  1,             2,            3,                   4,           5                       ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            250 + 150,           250 + 300,   500 + 600               ),
                ('EXP1 Expense 1',   1225,          0,            350,                 350,         525                     ),
                ('EXP2 Expense 2',   1680 + 225,    225,          600 * (10/30) + 0,   600 + 0,     600 * (1 + 14/30) + 225 ),
                ('Total',            5180,          225,          950,                 1500,        2730                    ),
            ],
            options,
        )

        # April 2023
        options = self.get_options('2023-04-01', '2023-04-30')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before               Current               Later
            [    0,                  1,             2,            3,                   4,                    5     ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            750 + 750,           250 + 300,            0     ),
                ('EXP1 Expense 1',   1225,          0,            1050,                175,                  0     ),
                ('EXP2 Expense 2',   1680 + 225,    0,            600 * (2 + 10/30),   600 * (14/30)+ 225,   0     ),
                ('Total',            5180,          0,            3950,                1230,                 0     ),
            ],
            options,
        )

        # May 2023
        options = self.get_options('2023-05-01', '2023-05-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # Q1 2023
        options = self.get_options('2023-01-01', '2023-03-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before   Current                  Later
            [    0,                  1,             2,            3,       4,                       5         ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            0,       750 + 750,               550       ),
                ('EXP1 Expense 1',   1225,          0,            0,       1050,                    175       ),
                ('EXP2 Expense 2',   1680 + 225,    225,          0,       600 * (2 + 10/30) + 0,   280 + 225 ),
                ('Total',            5180,          225,          0,       3950,                    1230      ),
            ],
            options,
        )

        # Q2 2023
        options = self.get_options('2023-04-01', '2023-06-30')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before               Current               Later
            [    0,                  1,             2,            3,                   4,                    5     ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            750 + 750,           250 + 300,            0     ),
                ('EXP1 Expense 1',   1225,          0,            1050,                175,                  0     ),
                ('EXP2 Expense 2',   1680 + 225,    0,            600 * (2 + 10/30),   600 * (14/30)+ 225,   0     ),
                ('Total',            5180,          0,            3950,                1230,                 0     ),
            ],
            options,
        )

        # 2022
        options = self.get_options('2022-01-01', '2022-12-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # 2023, nothing to show as all the moves have been deferred by the end of the year 2023
        options = self.get_options('2023-01-01', '2023-12-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

    def test_deferred_revenue_report(self):
        """
        Test the deferred revenue report with the 'month' method.
        We use multiple report months/quarters/years to check that the computation is correct.
        """
        self.company.deferred_revenue_amount_computation_method = 'month'
        self.create_invoice(self.revenue_lines, 'out_invoice')

        # December 2022
        options = self.get_options('2022-12-01', '2022-12-31', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # January 2023
        options = self.get_options('2023-01-01', '2023-01-31', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before   Current              Later
            [    0,                  1,             2,            3,       4,                   5                       ],
            [
                ('REV0 Revenue 0',   1000 + 1050,   0,            0,       250 + 150,           750 + 900               ),
                ('REV1 Revenue 1',   1225,          0,            0,       350,                 875                     ),
                ('REV2 Revenue 2',   1680 + 225,    225,          0,       600 * (10/30) + 0,   600 * (2 + 14/30) + 225 ),
                ('Total',            5180,          225,          0,       950,                 4230                    ),
            ],
            options,
        )

        # February 2023
        options = self.get_options('2023-02-01', '2023-02-28', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before               Current      Later
            [    0,                  1,             2,            3,                   4,           5                       ],
            [
                ('REV0 Revenue 0',   1000 + 1050,   0,            250 + 150,           250 + 300,   500 + 600               ),
                ('REV1 Revenue 1',   1225,          0,            350,                 350,         525                     ),
                ('REV2 Revenue 2',   1680 + 225,    225,          600 * (10/30) + 0,   600 + 0,     600 * (1 + 14/30) + 225 ),
                ('Total',            5180,          225,          950,                 1500,        2730                    ),
            ],
            options,
        )

        # April 2023
        options = self.get_options('2023-04-01', '2023-04-30', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before               Current               Later
            [    0,                  1,             2,            3,                   4,                    5     ],
            [
                ('REV0 Revenue 0',   1000 + 1050,   0,            750 + 750,           250 + 300,            0     ),
                ('REV1 Revenue 1',   1225,          0,            1050,                175,                  0     ),
                ('REV2 Revenue 2',   1680 + 225,    0,            600 * (2 + 10/30),   600 * (14/30)+ 225,   0     ),
                ('Total',            5180,          0,            3950,                1230,                 0     ),
            ],
            options,
        )

        # May 2023
        options = self.get_options('2023-05-01', '2023-05-31', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # Q1 2023
        options = self.get_options('2023-01-01', '2023-03-31', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before   Current                  Later
            [    0,                  1,             2,            3,       4,                       5         ],
            [
                ('REV0 Revenue 0',   1000 + 1050,   0,            0,       750 + 750,               550       ),
                ('REV1 Revenue 1',   1225,          0,            0,       1050,                    175       ),
                ('REV2 Revenue 2',   1680 + 225,    225,          0,       600 * (2 + 10/30) + 0,   280 + 225 ),
                ('Total',            5180,          225,          0,       3950,                    1230      ),
            ],
            options,
        )

        # Q2 2023
        options = self.get_options('2023-04-01', '2023-06-30', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before               Current               Later
            [    0,                  1,             2,            3,                   4,                    5     ],
            [
                ('REV0 Revenue 0',   1000 + 1050,   0,            750 + 750,           250 + 300,            0     ),
                ('REV1 Revenue 1',   1225,          0,            1050,                175,                  0     ),
                ('REV2 Revenue 2',   1680 + 225,    0,            600 * (2 + 10/30),   600 * (14/30)+ 225,   0     ),
                ('Total',            5180,          0,            3950,                1230,                 0     ),
            ],
            options,
        )

        # 2022
        options = self.get_options('2022-01-01', '2022-12-31', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # 2023: nothing to show since all the invoices are deferred
        options = self.get_options('2023-01-01', '2023-12-31', self.deferred_revenue_report)
        lines = self.get_lines(options, self.deferred_revenue_report)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

    def test_deferred_expense_report_days(self):
        """
        Test the deferred expense report with the 'day' method.
        We use multiple report months/quarters/years to check that the computation is correct.
        """
        self.company.deferred_expense_amount_computation_method = 'day'
        self.create_invoice(self.expense_lines)

        # December 2022
        options = self.get_options('2022-12-01', '2022-12-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

        # January 2023
        options = self.get_options('2023-01-01', '2023-01-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before   Current   Later
            [    0,                  1,             2,            3,       4,        5          ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            0,       418.33,   1631.67    ),
                ('EXP1 Expense 1',   1225,          0,            0,       361.67,   863.33     ),
                ('EXP2 Expense 2',   1680 + 225,    225,          0,       220,      1460 + 225 ),
                ('Total',            5180,          225,          0,       1000,     4180       ),
            ],
            options,
        )

        # February 2023
        options = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before    Current   Later
            [    0,                  1,             2,            3,        4,        5         ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            418.33,   513.33,   1118.33   ),
                ('EXP1 Expense 1',   1225,          0,            361.67,   326.67,   536.67    ),
                ('EXP2 Expense 2',   1680 + 225,    225,          220,      560,      900 + 225 ),
                ('Total',            5180,          225,          1000,     1400,     2780      ),
            ],
            options,
        )

        # April 2023
        options = self.get_options('2023-04-01', '2023-04-30')
        lines = self.get_lines(options)
        self.assertLinesValues(

            # ruff: noqa: E202

            lines,
            #    Name                Total          Not Started   Before    Current   Later
            [    0,                  1,             2,            3,        4,        5         ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            1500,     550,      0         ),
                ('EXP1 Expense 1',   1225,          0,            1050,     175,      0         ),
                ('EXP2 Expense 2',   1680 + 225,    0,            1400,     505,      0         ),
                ('Total',            5180,          0,            3950,     1230,     0         ),
            ],
            options,
        )

        # Q1 2023
        options = self.get_options('2023-01-01', '2023-03-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before   Current   Later
            [    0,                  1,             2,            3,       4,        5         ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            0,       1500,     550       ),
                ('EXP1 Expense 1',   1225,          0,            0,       1050,     175       ),
                ('EXP2 Expense 2',   1680 + 225,    225,          0,       1400,     280 + 225 ),
                ('Total',            5180,          225,          0,       3950,     1230      ),
            ],
            options,
        )

    def test_deferred_expense_report_filter_all_entries(self):
        """
        Test the 'All entries' option on the deferred expense report.
        """
        self.company.deferred_expense_amount_computation_method = 'day'
        self.create_invoice(self.expense_lines, post=True)
        self.create_invoice(self.expense_lines, post=False)

        # Only posted entries
        options = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before    Current   Later
            [    0,                  1,             2,            3,        4,        5         ],
            [
                ('EXP0 Expense 0',   1000 + 1050,   0,            418.33,   513.33,   1118.33   ),
                ('EXP1 Expense 1',   1225,          0,            361.67,   326.67,   536.67    ),
                ('EXP2 Expense 2',   1680 + 225,    225,          220,      560,      900 + 225 ),
                ('Total',            5180,          225,          1000,     1400,     2780      ),
            ],
            options,
        )

        # All non-cancelled entries
        options = self._generate_options(self.deferred_expense_report, fields.Date.from_string('2023-02-01'), fields.Date.from_string('2023-02-28'), {
            'all_entries': True,
        })
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total          Not Started   Before    Current    Later
            [    0,                  1,             2,            3,        4,         5          ],
            [
                ('EXP0 Expense 0',   2000 + 2100,   0,            836.67,   1026.67,   2236.67    ),
                ('EXP1 Expense 1',   2450,          0,            723.33,   653.33,    1073.33    ),
                ('EXP2 Expense 2',   3360 + 450,    450,          440,      1120,      1800 + 450 ),
                ('Total',            10360,         450,          2000,     2800,      5560       ),
            ],
            options,
        )

    def test_deferred_expense_report_comparison(self):
        """
        Test the the comparison tool on the deferred expense report.
        For instance, we select April 2023 and compare it with the last 4 months
        """
        self.create_invoice(self.expense_lines)

        # April 2023 + period comparison of last 4 months
        options = self.get_options('2023-04-01', '2023-04-30')
        options = self._update_comparison_filter(options, self.deferred_expense_report, 'previous_period', 4)
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Dec 2022   Jan 2023   Feb 2023   Mar 2023   Apr 2023 (Current)   Later
            [    0,                  1,      2,            3,       4,         5,         6,         7,         8,                   9     ],
            [
                ('EXP0 Expense 0',   2050,   0,            0,       0,         400,       550,       550,       550,                 0     ),
                ('EXP1 Expense 1',   1225,   0,            0,       0,         350,       350,       350,       175,                 0     ),
                ('EXP2 Expense 2',   1905,   0,            0,       0,         200,       600,       600,       505,                 0     ),
                ('Total',            5180,   0,            0,       0,         950,       1500,      1500,      1230,                0     ),
            ],
            options,
        )

    def test_deferred_expense_report_partially_deductible_tax(self):
        """
        Test the deferred expense report with partially deductible tax.
        If we have 50% deductible tax, half of the invoice line amount should also be deferred.
        Here, for an invoice line of 1000, and a tax of 40% partially deductible (50%) on 3 months, we will have:
        - 1400 for the total amount, tax included
        - 1200 for the total amount to be deferred (1000 + 400/2)
        - 400 for the deferred amount for each of the 3 months
        """
        partially_deductible_tax = self.env['account.tax'].create({
            'name': 'Partially deductible Tax',
            'amount': 40,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True
                }),
            ],
        })

        # Create invoice with 3 cars to be depreciated on different periods
        # to make sure the deferred dates are correctly copied on the right lines
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2022-01-01')
        for year in (2022, 2023, 2023):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.name = f"Car {year}"
                line_form.quantity = 1
                line_form.price_unit = 1000
                line_form.deferred_start_date = f'{year}-01-01'
                line_form.deferred_end_date = f'{year}-03-31'
                line_form.tax_ids.add(partially_deductible_tax)
                line_form.account_id = self.expense_accounts[0]
        move = move_form.save()
        move.action_post()

        # Taxes for 2023 should be aggregated into one because we have the same deferred dates.
        # Taxes for 2022 should not be aggregated with 2023 because we have different deferred dates.
        # Therefore we have 4 lines:
        #     - 3 for the cars
        #     - 1 for the tax of 2022
        #     - 1 for the aggregated taxes of 2023
        self.assertEqual(len(move.line_ids.filtered(lambda l: l.account_id == self.expense_accounts[0])), 5)

        # 2 cars (not 3) should appear with this date range
        options = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   2400,   0,            800,     800,      800   ),
                ('Total',            2400,   0,            800,     800,      800   ),
            ],
            options,
        )

    def test_deferred_expense_report_credit_notes(self):
        """
        Test the credit notes on the deferred expense report.
        """
        self.company.deferred_expense_amount_computation_method = 'day'
        self.create_invoice(self.expense_lines, move_type='in_refund')

        options = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total           Not Started   Before     Current    Later
            [    0,                  1,              2,            3,         4,         5          ],
            [
                ('EXP0 Expense 0',   -1000 - 1050,   0,            -418.33,   -513.33,   -1118.33   ),
                ('EXP1 Expense 1',   -1225,          0,            -361.67,   -326.67,   -536.67    ),
                ('EXP2 Expense 2',   -1680 - 225,    -225,         -220,      -560,      -900 - 225 ),
                ('Total',            -5180,          -225,         -1000,     -1400,     -2780      ),
            ],
            options,
        )

    def test_deferred_expense_report_compute_method_full_months(self):
        """
        Test the full_months method on the deferred expense report.
        """
        self.company.deferred_expense_amount_computation_method = 'full_months'
        self.create_invoice([[self.expense_accounts[0], 1200, '2023-01-31', '2024-01-30']])
        self.create_invoice([[self.expense_accounts[1], 1200, '2023-02-01', '2023-03-31']])
        self.create_invoice([[self.expense_accounts[2], 1200, '2023-02-01', '2023-03-16']])
        self.create_invoice([[self.expense_accounts[3], 1200, '2023-02-05', '2023-03-16']])
        self.create_invoice([[self.expense_accounts[4], 1200, '2023-02-05', '2023-03-31']])
        self.create_invoice([[self.expense_accounts[5], 1200, '2023-02-13', '2023-04-30']])
        self.create_invoice([[self.expense_accounts[6], 1200, '2023-03-01', '2023-06-18']])
        self.create_invoice([[self.expense_accounts[7], 1200, '2023-03-05', '2023-06-30']])
        self.create_invoice([[self.expense_accounts[8], 1200, '2023-03-13', '2024-03-12']])
        self.create_invoice([[self.expense_accounts[9], 1200, '2023-03-14', '2023-03-18']])

        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)

        for line in lines:
            total = line['columns'][0]['no_format']
            before = line['columns'][2]['no_format']  # 1 is "Not Started"
            current = line['columns'][3]['no_format']
            later = line['columns'][4]['no_format']
            self.assertAlmostEqual(total, before + current + later, 3)

        self.assertLinesValues(
            lines,
            #         Name          Total   Not Started   Before     Current   Later
            [0,                         1,            2,       3,         4,      5],
            [
                ('EXP0 Expense 0',   1200,            0,     200,       100,    900),
                ('EXP1 Expense 1',   1200,            0,     600,       600,      0),
                ('EXP2 Expense 2',   1200,            0,    1200,         0,      0),
                ('EXP3 Expense 3',   1200,            0,    1200,         0,      0),
                ('EXP4 Expense 4',   1200,            0,     600,       600,      0),
                ('EXP5 Expense 5',   1200,            0,     400,       400,    400),
                ('EXP6 Expense 6',   1200,            0,       0,       400,    800),
                ('EXP7 Expense 7',   1200,            0,       0,       300,    900),
                ('EXP8 Expense 8',   1200,            0,       0,       100,   1100),
                ('EXP9 Expense 9',   1200,            0,       0,      1200,      0),
                ('Total',           12000,            0,    4200,      3700,   4100),
            ],
            options,
        )

    def assert_invoice_lines(self, deferred_move, expected_values):
        for line, expected_value in zip(deferred_move.line_ids, expected_values):
            expected_account, expected_debit, expected_credit = expected_value
            self.assertRecordValues(line, [{
                'account_id': expected_account.id,
                'debit': expected_debit,
                'credit': expected_credit,
            }])

    def test_deferred_expense_report_accounting_date(self):
        """
        Test that the accounting date is taken into account for the deferred expense report.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.create_invoice([self.expense_lines[0]], invoice_date='2023-02-15')

        # In january, the move is not accounted yet (accounting date is in 15 Feb), so nothing should be displayed.
        options = self.get_options('2023-01-01', '2023-01-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )
        # Nothing should be generated either.
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options)

        # In Feb, the move is accounted, so it should be displayed.
        options = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   0,            250,     250,      500   ),
                ('Total',            1000,   0,            250,     250,      500   ),
            ],
            options,
        )

        # Same in March.
        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   0,            500,     250,      250   ),
                ('Total',            1000,   0,            500,     250,      250   ),
            ],
            options,
        )

        # Same in April.
        options = self.get_options('2023-04-01', '2023-04-30')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   0,            750,     250,      0     ),
                ('Total',            1000,   0,            750,     250,      0     ),
            ],
            options,
        )

        # In May, the move is accounted and fully deferred, so it should not be displayed.
        options = self.get_options('2023-05-01', '2023-05-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name   Total   Not Started   Before   Current   Later
            [    0,     1,      2,            3,       4,        5     ],
            [],
            options,
        )

    def test_deferred_expense_generate_grouped_entries_method(self):
        """
        Test the Generate entries button on the deferred expense report.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'

        options = self.get_options('2023-01-01', '2023-01-31')

        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options)

        # Create 3 different invoices (instead of one with 3 lines)
        for expense_line in self.expense_lines[:3]:
            self.create_invoice([expense_line])

        # Check that no deferred move has been created
        self.assertEqual(self.env['account.move.line'].search_count([('account_id', '=', self.deferral_account.id)]), 0)

        # Generate the grouped deferred entries
        generated_entries_january = self.generate_deferral_entries(options)

        deferred_move_january = generated_entries_january[0]
        self.assertRecordValues(deferred_move_january, [{
            'state': 'posted',
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-01-31'),
        }])
        expected_values_january = [
            #        Account                         Debit                       Credit
            [self.expense_accounts[0],                                     0, 1000 + 1050],
            [self.expense_accounts[0],                             250 + 150,           0],
            [self.expense_accounts[1],                                     0,        1225],
            [self.expense_accounts[1],                                   350,           0],
            [self.deferral_account,     1000 + 1050 + 1225 - 250 - 150 - 350,           0]
        ]
        self.assert_invoice_lines(deferred_move_january, expected_values_january)

        deferred_inverse_january = generated_entries_january[1]
        self.assertEqual(deferred_inverse_january.move_type, 'entry')
        self.assertEqual(deferred_inverse_january.state, 'posted')  # Posted because the date is before today
        self.assertEqual(deferred_inverse_january.date, fields.Date.from_string('2023-02-01'))

        # Don't re-generate entries for the same period if they already exist for all move lines
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options)

        # Generate the grouped deferred entries for the next period
        generated_entries_february = self.generate_deferral_entries(self.get_options('2023-02-01', '2023-02-28'))
        deferred_move_february = generated_entries_february[0]
        expected_values_february = [
            #        Account                         Debit                       Credit
            [self.expense_accounts[0],                                     0, 1000 + 1050],
            [self.expense_accounts[0],                             500 + 450,           0],
            [self.expense_accounts[1],                                     0,        1225],
            [self.expense_accounts[1],                                   700,           0],
            [self.deferral_account,     1000 + 1050 + 1225 - 500 - 450 - 700,           0]
        ]
        self.assert_invoice_lines(deferred_move_february, expected_values_february)

    def _test_deferred_expense_partially_generate_grouped_entries_method_common(self):
        """
        Test that if we generate the deferrals for a period, we don't re-generate them if they already exist.
        and we regenerate them if necessary (e.g. a new invoice has been created for the same period).
        """
        self.company.generate_deferred_expense_entries_method = 'manual'

        options = self.get_options('2023-01-01', '2023-01-31')

        # Create 2 different invoices (instead of one with 2 lines)
        self.create_invoice([self.expense_lines[0]])
        self.create_invoice([self.expense_lines[1]])

        # Generate the grouped deferred entries
        generated_entries_january = self.generate_deferral_entries(options)

        deferred_move_january, deferred_inverse_january = generated_entries_january
        self.assertRecordValues(deferred_move_january, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-01-31'),
        }])
        expected_values_january = [
            #        Account                    Debit               Credit
            [self.expense_accounts[0],                        0,  1000 + 1050],
            [self.expense_accounts[0],                250 + 150,            0],
            [self.deferral_account,     1000 + 1050 - 250 - 150,            0]
        ]
        self.assert_invoice_lines(deferred_move_january, expected_values_january)

        self.assertRecordValues(deferred_inverse_january, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-02-01'),
        }])

        # Don't re-generate entries for the same period if they already exist for all move lines
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options)

        # Let's create a new invoice that should be shown in the January period
        self.create_invoice([self.expense_lines[2]])

        # Now, even though we have already generated the grouped deferral for January,
        # we must re-generate it because we have a new invoice that should be included in the January period.
        # We only generate the missing part
        generated_entries_january2 = self.generate_deferral_entries(options)
        deferred_move_january2 = generated_entries_january2[0]
        self.assertRecordValues(deferred_move_january2, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-01-31'),
        }])
        expected_values_january2 = [
            #        Account              Debit          Credit
            [self.expense_accounts[1],           0,        1225],
            [self.expense_accounts[1],         350,           0],
            [self.deferral_account,     1225 - 350,           0]
        ]
        self.assert_invoice_lines(deferred_move_january2, expected_values_january2)
        return deferred_move_january, deferred_inverse_january

    def test_deferred_expense_partially_generate_grouped_entries_method_past_period(self):
        """
        Test that if we generate the deferrals for a period, we don't re-generate them if they already exist.
        and we regenerate them if necessary (e.g. a new invoice has been created for the same period).
        """
        deferred_move_january, deferred_inverse_january = self._test_deferred_expense_partially_generate_grouped_entries_method_common()
        self.assertEqual(deferred_move_january.state, 'posted')  # January is in the past so the move is posted
        self.assertEqual(deferred_inverse_january.state, 'posted')

    @freeze_time('2023-01-01')
    def test_deferred_expense_partially_generate_grouped_entries_method_current_period(self):
        """
        Same as previous test but for an ongoing month. This test has been added after discovering
        that if you generate the deferrals for the current month, you could generate them again
        and again. This is because the generated deferral is only posted at then end of the month
        (date_to of the report period). So the `filter_generated_entries` wasn't working as expected
        The test is exactly the same as the previous one, we with a freeze_time simulating Jan 2023
        """
        deferred_move_january, deferred_inverse_january = self._test_deferred_expense_partially_generate_grouped_entries_method_common()
        self.assertEqual(deferred_move_january.state, 'draft')  # January is still current so the move is not posted yet
        self.assertEqual(deferred_inverse_january.state, 'draft')

    @freeze_time('2023-01-01')
    def test_deferred_expense_partially_generate_grouped_entries_method_later_period(self):
        """
        Same as previous test but for a later month (February 2023 while we simulate we are in Jan 2023)
        """
        self.company.generate_deferred_expense_entries_method = 'manual'

        options = self.get_options('2023-02-01', '2023-02-28')

        # Create 2 different invoices (instead of one with 2 lines)
        self.create_invoice([self.expense_lines[0]])
        self.create_invoice([self.expense_lines[1]])

        # Generate the grouped deferred entries
        generated_entries_february = self.generate_deferral_entries(options)

        deferred_move_february, deferred_inverse_february = generated_entries_february
        self.assertRecordValues(deferred_move_february, [{
            'state': 'draft',  # Not posted yet since it's in the future
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-02-28'),
        }])
        expected_values_february = [
            #        Account                    Debit               Credit
            [self.expense_accounts[0],                        0,  1000 + 1050],
            [self.expense_accounts[0],                500 + 450,            0],
            [self.deferral_account,     1000 + 1050 - 500 - 450,            0]
        ]
        self.assert_invoice_lines(deferred_move_february, expected_values_february)

        self.assertRecordValues(deferred_inverse_february, [{
            'state': 'draft',  # Not posted yet since it's in the future
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-03-01'),
        }])

        # Don't re-generate entries for the same period if they already exist for all move lines
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options)

        # Let's create a new invoice that should be shown in the february period
        self.create_invoice([self.expense_lines[2]])

        # Now, even though we have already generated the grouped deferral for february,
        # we must re-generate it because we have a new invoice that should be included in the february period.
        # We only generate the missing part
        generated_entries_february2 = self.generate_deferral_entries(options)
        deferred_move_february2 = generated_entries_february2[0]
        self.assertRecordValues(deferred_move_february2, [{
            'state': 'draft',  # Not posted yet since it's in the future
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-02-28'),
        }])
        expected_values_february2 = [
            #        Account              Debit          Credit
            [self.expense_accounts[1],           0,        1225],
            [self.expense_accounts[1],         700,           0],
            [self.deferral_account,     1225 - 700,           0]
        ]
        self.assert_invoice_lines(deferred_move_february2, expected_values_february2)

    def test_deferred_expense_generate_future_deferrals_grouped(self):
        """
        Test the Generate entries button when we have a deferral starting after the invoice period.
        """
        self.company.deferred_expense_amount_computation_method = 'month'
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.create_invoice([[self.expense_accounts[0], 750, '2023-03-01', '2023-04-15']])

        # JANUARY
        generated_entries_january = self.generate_deferral_entries(self.get_options('2023-01-01', '2023-01-31'))

        # January Deferral
        deferred_move_january = generated_entries_january[0]
        self.assertRecordValues(deferred_move_january, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-01-31'),
        }])
        expected_values_january = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],         0,       750],
            [self.deferral_account,          750,         0],
        ]
        self.assert_invoice_lines(deferred_move_january, expected_values_january)

        # January Reversal
        deferred_inverse_january = generated_entries_january[1]
        self.assertRecordValues(deferred_inverse_january, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-02-01'),
        }])
        expected_values_inverse_january = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],       750,         0],
            [self.deferral_account,            0,       750],
        ]
        self.assert_invoice_lines(deferred_inverse_january, expected_values_inverse_january)

        # FEBRUARY
        generated_entries_february = self.generate_deferral_entries(self.get_options('2023-02-01', '2023-02-28'))

        # February Deferral
        deferred_move_february = generated_entries_february[0]
        self.assertRecordValues(deferred_move_february, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-02-28'),
        }])
        expected_values_february = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],         0,       750],
            [self.deferral_account,          750,         0],
        ]
        self.assert_invoice_lines(deferred_move_february, expected_values_february)

        # February Reversal
        deferred_inverse_february = generated_entries_february[1]
        self.assertRecordValues(deferred_inverse_february, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-03-01'),
        }])
        expected_values_inverse_february = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],       750,         0],
            [self.deferral_account,            0,       750],
        ]
        self.assert_invoice_lines(deferred_inverse_february, expected_values_inverse_february)

        # MARCH
        generated_entries_march = self.generate_deferral_entries(self.get_options('2023-03-01', '2023-03-31'))

        # March Deferral
        deferred_move_march = generated_entries_march[0]
        self.assertRecordValues(deferred_move_march, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-03-31'),
        }])
        expected_values_march = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],         0,       750],
            [self.expense_accounts[0],       500,         0],
            [self.deferral_account,          250,         0],
        ]
        self.assert_invoice_lines(deferred_move_march, expected_values_march)

        # March Reversal
        deferred_inverse_march = generated_entries_march[1]
        self.assertRecordValues(deferred_inverse_march, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-04-01'),
        }])
        expected_values_inverse_march = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],       750,         0],
            [self.expense_accounts[0],         0,       500],
            [self.deferral_account,            0,       250],
        ]
        self.assert_invoice_lines(deferred_inverse_march, expected_values_inverse_march)

        # APRIL
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            # No entry should be generated, since everything has been deferred.
            self.generate_deferral_entries(self.get_options('2023-04-01', '2023-04-30'))

    def test_deferred_revenue_generate_grouped_without_taxes(self):
        """
        Test the default taxes on accounts are ignored when generating a grouped deferral entry.
        """
        self.company.generate_deferred_revenue_entries_method = 'manual'
        deferral_account = self.company_data['default_account_deferred_revenue']
        revenue_account_with_taxes = self.env['account.account'].create({
            'name': 'Revenue with Taxes',
            'code': 'REVWTAXES',
            'account_type': 'income',
            'tax_ids': [Command.set(self.tax_sale_a.ids)]
        })
        options = self.get_options('2023-01-01', '2023-01-31', self.deferred_revenue_report)
        revenue_handler = self.env['account.deferred.revenue.report.handler']

        self.create_invoice([[revenue_account_with_taxes, 1000, '2023-01-01', '2023-04-30']], move_type='out_invoice')

        # Check that no deferred move has been created
        self.assertEqual(self.env['account.move.line'].search_count([('account_id', '=', deferral_account.id)]), 0)

        # Generate the grouped deferred entries
        generated_entries_january = self.generate_deferral_entries(options, revenue_handler)

        deferred_move_january = generated_entries_january[0]
        self.assertRecordValues(deferred_move_january, [{
            'state': 'posted',
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-01-31'),
        }])
        expected_values_january = [
            # Account                         Debit       Credit
            [revenue_account_with_taxes,       1000,           0],
            [revenue_account_with_taxes,          0,         250],
            [deferral_account,                    0,         750],
        ]
        self.assert_invoice_lines(deferred_move_january, expected_values_january)
        # There are no extra (tax) lines besides the three lines we checked before
        self.assertFalse(deferred_move_january.line_ids.tax_line_id)

    def test_deferred_values_rounding(self):
        """
        When using the manually & grouped method, we might have some rounding issues
        when aggregating multiple deferred entries. This test ensures that the rounding
        is done correctly.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.company.deferred_expense_amount_computation_method = 'day'
        self.create_invoice([[self.expense_accounts[0], 600, '2023-04-04', '2023-05-25']])
        self.create_invoice([[self.expense_accounts[1], 600, '2023-04-05', '2023-05-16']])
        self.create_invoice([[self.expense_accounts[0], 600, '2023-04-04', '2023-05-08']])

        # This shouldn't raise an error like this 'The total of debits equals $1,800.01 and the total of credits equals $1,800.00.'
        self.generate_deferral_entries(self.get_options('2023-04-01', '2023-04-30'))

    def test_deferred_single_rounding(self):
        """
        When using the manually & grouped method, we might have some rounding issues
        due to rounding in different places. This test ensures that the a balance line is created
        automatically for the difference.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.company.deferred_expense_amount_computation_method = 'month'
        self.create_invoice([[self.expense_accounts[0], 4.95, '2023-01-01', '2023-10-31']])

        # This shouldn't raise an error like this 'The total of debits equals $4.96 and the total of credits equals $4.95.'
        generated_entries = self.generate_deferral_entries(self.get_options('2023-01-01', '2023-01-31'))

        deferral_move = generated_entries[0]
        expected_values = [
            # Account                         Debit       Credit
            [self.expense_accounts[0],           0,         4.95],
            [self.expense_accounts[0],        0.50,            0],
            [self.deferral_account,           4.46,            0],
            [self.deferral_account,              0,         0.01],
        ]
        # The balance line was added for the rounding error
        self.assert_invoice_lines(deferral_move, expected_values)

    def test_deferred_fully_inside_report_period(self):
        """
        If the invoice is fully inside the report period, nothing should be generated.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.company.deferred_expense_amount_computation_method = 'month'

        # The report should be empty because the invoice date, and the deferred dates are all in inside the report period
        # Nothing should be reversed, displayed or generated because the invoice is already in the correct period
        move1 = self.create_invoice([[self.expense_accounts[0], 600, '2023-01-15', '2023-01-30']], invoice_date='2023-01-15')
        options_january = self.get_options('2023-01-01', '2023-01-31')
        lines = self.get_lines(options_january)
        self.assertLinesValues(
            lines,
            #   Name              Total      Before    Current     Later
            [   0,                  1,          2,        3,        4     ],
            [],
            options_january,
        )
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options_january)

        move1.button_cancel()

        # The report should be NOT empty because the invoice date is prior the report date (even if
        # the deferred dates are all in inside the report period) because we need to be able to
        # reverse the invoice in january and account for it in the correct period (in february here).
        self.create_invoice([[self.expense_accounts[0], 1000, '2023-02-10', '2023-02-28']], invoice_date='2023-01-01')

        # In january, the invoice exists, and the 'To defer' (Later) column should not be empty
        lines = self.get_lines(options_january)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   1000,         0,       0,        1000  ),
                ('Total',            1000,   1000,         0,       0,        1000  ),
            ],
            options_january,
        )

        # The invoice should be reversed in january so that it can be accounted for in february
        generated_entries = self.generate_deferral_entries(options_january)

        deferral_move_january = generated_entries[0]
        self.assertEqual(deferral_move_january.date, fields.Date.to_date('2023-01-31'))
        expected_values_january = [
            # Account                         Debit       Credit
            [self.expense_accounts[0],          0,        1000],
            [self.deferral_account,          1000,           0],
        ]
        self.assert_invoice_lines(deferral_move_january, expected_values_january)

        # In february, the invoice exists, and is being accounted for (Current column)
        options_february = self.get_options('2023-02-01', '2023-02-28')
        lines = self.get_lines(options_february)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   0,            0,       1000,     0     ),
                ('Total',            1000,   0,            0,       1000,     0     ),
            ],
            options_february,
        )

        # The invoice is now accounted for in february, so nothing should be generated
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options_february)

    def test_deferred_same_date(self):
        """
        A bug has been found where having an invoice with a start and end date on the last day
        of the month would cause a division by zero error. This test ensures that this bug is fixed.
        Here, the deferred dates are not inside the report period.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.company.deferred_expense_amount_computation_method = 'month'
        self.create_invoice([[self.expense_accounts[0], 1000, '2023-10-30', '2023-10-30']])

        options_sept = self.get_options('2023-09-01', '2023-09-30')
        lines = self.get_lines(options_sept)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   1000,         0,       0,        1000  ),
                ('Total',            1000,   1000,         0,       0,        1000  ),
            ],
            options_sept,
        )

        generated_entries = self.generate_deferral_entries(options_sept)

        deferral_move = generated_entries[0]
        self.assertEqual(deferral_move.date, fields.Date.to_date('2023-09-30'))
        expected_values = [
            # Account                         Debit       Credit
            [self.expense_accounts[0],          0,        1000],
            [self.deferral_account,          1000,           0],
        ]
        self.assert_invoice_lines(deferral_move, expected_values)

    def test_deferred_expense_change_grouped_entries_method(self):
        """
        Test the change of the deferred expense method from on_validation to manual
        """
        self.company.generate_deferred_expense_entries_method = 'on_validation'

        self.create_invoice([self.expense_lines[0]])
        self.assertEqual(self.env['account.move.line'].search_count([('account_id', '=', self.deferral_account.id)]), 5)  # 4 months + 1 for the initial deferred invoice

        # When changing the method to manual, the deferred entries should not be re-generated
        self.company.generate_deferred_expense_entries_method = 'manual'
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(self.get_options('2023-02-01', '2023-02-28'))

    def test_deferred_expense_manual_generation_totally_deferred(self):
        """
        In manual mode generation, if the lines are totally deferred,
        then no entry should be generated.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'

        self.create_invoice([[self.expense_accounts[0], 1000, '2023-01-01', '2023-04-30']])
        self.generate_deferral_entries(self.get_options('2023-03-01', '2023-03-31'))
        self.assertEqual(self.env['account.move.line'].search_count([('account_id', '=', self.deferral_account.id)]), 2)

        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(self.get_options('2023-04-01', '2023-04-30'))

        move2 = self.create_invoice([[self.expense_accounts[1], 1000, '2023-01-01', '2023-05-31']])
        generated_entry = self.generate_deferral_entries(self.get_options('2023-04-01', '2023-04-30'))[0]
        self.assertEqual(len(generated_entry.line_ids), 3)  # 3 lines, not 6 because move1 is totally deferred
        self.assertEqual(generated_entry.deferred_original_move_ids, move2)  # not move1

    def test_deferred_expense_manual_generation_only_posted(self):
        """
        In manual mode generation, even if the filter shows draft moves,
        then no entry should be generated for draft moves.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'

        self.create_invoice([self.expense_lines[0]], post=False)
        options = self.get_options('2023-01-01', '2023-01-31')
        options['all_entries'] = True
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options)

    def test_deferred_expense_manual_generation_after_on_validation(self):
        """
        In manual mode, you should still be able to generate an deferral entry for a period
        when there already exists a deferral entry from a former on_validation mode on the same date,
        and that entry should not defer the already deferred amount from the automatic entry in that
        same period.
        """
        # First post an invoice with the on_validation method, creating deferrals
        move = self.create_invoice([self.expense_lines[0]])
        # Check that the deferral moves have been created (1 + 4)
        self.assertEqual(len(move.deferred_move_ids), 5)

        # Switch to manual mode
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.create_invoice([self.expense_lines[0]])

        options = self.get_options('2023-01-01', '2023-01-31')
        generated_entries_jan = self.generate_deferral_entries(options)

        deferred_move_jan = generated_entries_jan[0]
        self.assertRecordValues(deferred_move_jan, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-01-31'),
        }])
        expected_values_jan = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],         0,      1000],
            [self.expense_accounts[0],       250,         0],
            [self.deferral_account,          750,         0],
        ]
        self.assert_invoice_lines(deferred_move_jan, expected_values_jan)

        # Reversal
        deferred_inverse_jan = generated_entries_jan[1]
        self.assertRecordValues(deferred_inverse_jan, [{
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-02-01'),
        }])
        expected_values_inverse_jan = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],      1000,         0],
            [self.expense_accounts[0],         0,       250],
            [self.deferral_account,            0,       750],
        ]
        self.assert_invoice_lines(deferred_inverse_jan, expected_values_inverse_jan)

    def test_deferred_expense_manual_generation_old_moves(self):
        """Test that old moves are not taken into account when generating deferred entries."""
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.company.deferred_expense_amount_computation_method = 'month'

        self.create_invoice([(self.expense_accounts[0], 1200, '2022-01-01', '2022-12-31')])
        self.create_invoice([(self.expense_accounts[0], 1200, '2023-01-01', '2023-12-31')])

        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1200,   0,            200,     100,      900   ),
                ('Total',            1200,   0,            200,     100,      900   ),
            ],
            options,
        )

        expected_values = (
            #        Account           Debit    Credit
            (self.expense_accounts[0],     0,    1200),
            (self.expense_accounts[0],   300,       0),
            (self.deferral_account,      900,       0),
        )
        deferral = self.generate_deferral_entries(options)[0]
        self.assert_invoice_lines(deferral, expected_values)

    def test_deferred_expense_manual_generation_deprecated_account(self):
        """Test that deferred on deprecated accounts are still visible in the report, but cannot be generated."""
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.company.deferred_expense_amount_computation_method = 'month'

        self.create_invoice([self.expense_lines[0]])
        self.expense_accounts[0].deprecated = True

        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   0,            500,     250,      250   ),
                ('Total',            1000,   0,            500,     250,      250   ),
            ],
            options,
        )

        # Shouldn't raise
        #    'The account ... is deprecated.'
        # or 'A line of this move is using a deprecated account, you cannot post it.'
        entries = self.generate_deferral_entries(options)
        expected_values = [
            # Account                      Debit     Credit
            [self.expense_accounts[0],         0,      1000],
            [self.expense_accounts[0],       750,         0],
            [self.deferral_account,          250,         0],
        ]
        self.assert_invoice_lines(entries[0], expected_values)

    def test_deferred_expense_manual_generation_go_backwards_in_time(self):
        """
        In manual mode generation, if we generate the deferral entries for
        a given month, we should still be able to generate the entries for
        the months prior to this one.
        """
        self.company.deferred_expense_amount_computation_method = 'month'
        self.company.generate_deferred_expense_entries_method = 'manual'

        # No entries yet for August
        options_august = self.get_options('2023-08-01', '2023-08-31')
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options_august)

        self.create_invoice([[self.expense_accounts[0], 600, '2023-07-01', '2023-09-30']])

        # Check that no deferred move has been created yet
        self.assertEqual(self.env['account.move.line'].search_count([('account_id', '=', self.deferral_account.id)]), 0)

        # Generate the grouped deferred entries for August (before doing it for July)
        generated_entries_august = self.generate_deferral_entries(options_august)
        deferred_move_august = generated_entries_august[0]
        expected_values_august = (
            #        Account           Debit    Credit
            (self.expense_accounts[0],     0,    600),
            (self.expense_accounts[0],   400,      0),
            (self.deferral_account,      200,      0),
        )
        self.assert_invoice_lines(deferred_move_august, expected_values_august)

        # Don't re-generate entries for the same period if they already exist for all move lines
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options_august)

        # Generate the grouped deferred entries for July
        options_july = self.get_options('2023-07-01', '2023-07-31')
        generated_entries_july = self.generate_deferral_entries(options_july)
        self.assertRecordValues(generated_entries_july, [{
            'state': 'posted',
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-07-31'),
        }, {
            'state': 'posted',
            'move_type': 'entry',
            'date': fields.Date.to_date('2023-08-01'),
        }])
        deferred_move_july, reversed_deferred_move_july = generated_entries_july
        expected_values_july = (
            #        Account           Debit    Credit
            (self.expense_accounts[0],     0,    600),
            (self.expense_accounts[0],   200,      0),
            (self.deferral_account,      400,      0),
        )
        expected_values_july_reversed = (
            #        Account           Debit    Credit
            (self.expense_accounts[0],   600,      0),
            (self.expense_accounts[0],     0,    200),
            (self.deferral_account,        0,    400),
        )
        self.assert_invoice_lines(deferred_move_july, expected_values_july)
        self.assert_invoice_lines(reversed_deferred_move_july, expected_values_july_reversed)

        # Don't re-generate entries for the same period if they already exist for all move lines
        with self.assertRaisesRegex(UserError, 'No entry to generate.'):
            self.generate_deferral_entries(options_july)

    def test_deferred_expense_manual_generation_single_period(self):
        """
        If we have an invoice covering only one period, we should only avoid creating deferral entries when the invoice
        date is the same as the period for the deferral. Otherwise we should still generate a deferral entry.
        """
        self.company.deferred_expense_amount_computation_method = 'month'
        self.company.generate_deferred_expense_entries_method = 'manual'

        self.create_invoice([[self.expense_accounts[0], 1000, '2023-02-01', '2023-02-28']])

        self.generate_deferral_entries(self.get_options('2023-01-01', '2023-01-31'))
        self.assertEqual(self.env['account.move.line'].search_count([('account_id', '=', self.deferral_account.id)]), 2)

    def test_deferred_expense_generation_lock_date(self):
        """
        Test that we cannot generate entries for a period that is locked.
        """
        self.company.deferred_expense_amount_computation_method = 'month'
        self.company.generate_deferred_expense_entries_method = 'manual'

        move = self.create_invoice([[self.expense_accounts[0], 1000, '2023-01-01', '2023-04-30']])

        move.company_id.fiscalyear_lock_date = fields.Date.to_date('2023-02-28')

        with self.assertRaisesRegex(UserError, 'You cannot generate entries for a period that is locked.'):
            self.generate_deferral_entries(self.get_options('2023-01-01', '2023-01-31'))

    def test_deferred_expense_manual_generation_reset_to_draft(self):
        """Test that the deferred entries cannot be deleted in the manual mode"""

        # On validation, we can reset to draft
        self.company.deferred_expense_amount_computation_method = 'month'
        move = self.create_invoice([(self.expense_accounts[0], 1680, '2023-01-21', '2023-04-14')])
        self.assertEqual(len(move.deferred_move_ids), 5)
        move.button_draft()
        self.assertFalse(move.deferred_move_ids)
        move.action_post()  # Repost

        # Let's switch to manual mode
        self.company.generate_deferred_expense_entries_method = 'manual'

        # We should still be able to reset to draft a move that was created with the on_validation mode
        move.button_draft()
        self.assertFalse(move.deferred_move_ids)

        # If the grouped deferral entry is the aggregation of only one invoice, we can reset the invoice to draft
        move3 = self.create_invoice([(self.expense_accounts[0], 1680, '2023-03-21', '2023-06-14')])
        self.generate_deferral_entries(self.get_options('2023-03-01', '2023-03-31'))
        move3.button_draft()
        self.assertFalse(move.deferred_move_ids)

        # If the grouped deferral entry is the aggregation of more than one invoice, we cannot reset to draft any of those to draft
        move4 = self.create_invoice([(self.expense_accounts[0], 1680, '2023-03-21', '2023-06-14')])
        move5 = self.create_invoice([(self.expense_accounts[0], 1680, '2023-03-21', '2023-06-14')])
        self.generate_deferral_entries(self.get_options('2023-03-01', '2023-03-31'))
        with self.assertRaisesRegex(UserError, 'You cannot reset to draft an invoice that is grouped in deferral entry. You can create a credit note instead.'):
            move4.button_draft()
        with self.assertRaisesRegex(UserError, 'You cannot reset to draft an invoice that is grouped in deferral entry. You can create a credit note instead.'):
            move5.button_draft()

    def test_deferred_expense_on_validation_generation_analytic_distribution(self):
        """Test that the analytic distribution of the invoice is transferred the deferred entries generated on validation."""

        analytic_plan_a = self.env['account.analytic.plan'].create({
            'name': 'Plan A',
        })
        aa_a1 = self.env['account.analytic.account'].create({
            'name': 'Account A1',
            'plan_id': analytic_plan_a.id
        })
        aa_a2 = self.env['account.analytic.account'].create({
            'name': 'Account A2',
            'plan_id': analytic_plan_a.id
        })
        move = self.create_invoice([self.expense_lines[0]], post=False)
        move.write({'invoice_line_ids': [
            Command.update(move.invoice_line_ids.id, {'analytic_distribution': {str(aa_a1.id): 60.0, str(aa_a2.id): 40.0}}),
        ]})
        self.env['account.move.line'].flush_model()
        move.action_post()
        expected_analytic_distribution = {str(aa_a1.id): 60.0, str(aa_a2.id): 40.0}
        for line in move.deferred_move_ids.line_ids:
            self.assertEqual(line.analytic_distribution, expected_analytic_distribution)

    def test_deferred_expense_manual_generation_analytic_distribution(self):
        """
        When using the manually & grouped method, the analytic distribution of the deferred entries
        should be computed according to the proportion between the deferred amount of each account
        and the total deferred amount.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'

        analytic_plan_a = self.env['account.analytic.plan'].create({
            'name': 'Plan A',
        })
        analytic_plan_b = self.env['account.analytic.plan'].create({
            'name': 'Plan B',
        })
        aa_a1 = self.env['account.analytic.account'].create({
            'name': 'Account A1',
            'plan_id': analytic_plan_a.id
        })
        aa_a2 = self.env['account.analytic.account'].create({
            'name': 'Account A2',
            'plan_id': analytic_plan_a.id
        })
        aa_a3 = self.env['account.analytic.account'].create({
            'name': 'Account A3',
            'plan_id': analytic_plan_a.id
        })
        aa_b1 = self.env['account.analytic.account'].create({
            'name': 'Account B1',
            'plan_id': analytic_plan_b.id
        })
        aa_b2 = self.env['account.analytic.account'].create({
            'name': 'Account B2',
            'plan_id': analytic_plan_b.id
        })
        # Test the account move lines with the following analytic distribution:
        #
        #    # |  Expense Account |   Amount   |        Analytic Distribution
        #    ------------------------------------------------------------------------
        #    1 |    Expense 0     |    1200    | {A1: 60%, A2: 40%, B1: 50%, B2: 50%}
        #    2 |    Expense 0     |    2400    | {A1: 100%}
        #    3 |    Expense 1     |    1200    | {A1: 50%, A3: 50%}
        #    4 |    Expense 1     |    1200    | NULL

        invoice_lines = [
            [self.expense_accounts[0], 1200, '2023-01-01', '2023-12-31'],
            [self.expense_accounts[0], 2400, '2023-01-01', '2023-12-31'],
            [self.expense_accounts[1], 1200, '2023-01-01', '2023-12-31'],
            [self.expense_accounts[1], 1200, '2023-01-01', '2023-12-31'],
        ]
        move = self.create_invoice(invoice_lines, post=False)
        move.write({'invoice_line_ids': [
            Command.update(move.invoice_line_ids[0].id,
                {'analytic_distribution': {str(aa_a1.id): 60.0, str(aa_a2.id): 40.0, str(aa_b1.id): 50.0, str(aa_b2.id): 50.0}}
            ),
            Command.update(move.invoice_line_ids[1].id,{'analytic_distribution': {str(aa_a1.id): 100.0}}),
            Command.update(move.invoice_line_ids[2].id, {'analytic_distribution': {str(aa_a1.id): 50.0, str(aa_a3.id): 50.0}}),
        ]})
        self.env['account.move.line'].flush_model()
        move.action_post()

        # Generate the grouped deferred entries
        generated_entries = self.generate_deferral_entries(self.get_options('2023-01-01', '2023-08-31'))

        # Details of the computation:
        #    Total Amount (Deferral Account): 1200 + 2400 + 1200 + 1200 = 6000
        #    Amount for Expense 0: 1200 + 2400 = 3600
        #    Amount for Expense 1: 1200 + 1200 = 2400
        #    ___________________________________________________________________________________________________________________
        #      |        |                    |                   |  Distribution by expense (*)   |  Deferral distribution (**)
        #    # | Amount |   Expense ratio    |    Total ratio    | (distribution / expense ratio) | (distribution / total ratio)
        #    -------------------------------------------------------------------------------------------------------------------
        #    1 |  1200  | 1200 / 3600 = 0.33 | 1200 / 6000 = 0.2 | A1 = 60% * 0.33 = 20%          | A1 = 60% * 0.2 = 12%
        #      |        | (0.33333333333...) |                   | A2 = 40% * 0.33 = 13.33%       | A2 = 40% * 0.2 = 8%
        #      |        |                    |                   | B1, B2 = 50% * 0.33 = 16.67%   | B1, B2 = 50% * 0.2 = 10%
        #    -------------------------------------------------------------------------------------------------------------------
        #    2 |  1200  | 2400 / 3600 = 0.67 | 2400 / 6000 = 0.4 | A1 = 100% * 0.67 = 66.67%      | A1 = 100% * 0.4 = 40%
        #    -------------------------------------------------------------------------------------------------------------------
        #    3 |  1200  | 1200 / 2400 = 0.5  | 1200 / 6000 = 0.2 | A1, A3 = 50% * 0.5 = 25%       | A1, A3 = 50% * 0.2 = 10%
        #    -------------------------------------------------------------------------------------------------------------------
        #    4 |  1200  | 1200 / 2400 = 0.5  | 1200 / 6000 = 0.2 |              NULL              |             NULL
        #
        # The analytic distribution of the deferred entries should be:
        # - Expense 0: {A1: 86.67%, A2: 13.33%, B1: 16.67%, B2: 16.67%}    [Sum of column (*) of line #1 and #2]
        # - Expense 1: {A1: 25%, A3: 25%}                                  [Sum of column (*) of line #3 and #4]
        # - Deferral Account: {A1: 62%, A2: 8%, B1: 10%, B2: 10%, A3: 10%} [Sum of column (**) of all 4 lines]
        #
        # The 2 generated entries should be the "Grouped Deferral Entry of Aug 2023" and its reversal.
        #
        #    "Grouped Deferral Entry of Aug 2023":
        #
        #         Account     |              Analytic Distribution               | Debit | Credit
        #    -------------------------------------------------------------------------------------
        #       Expense 0     | {A1: 86.67%, A2: 13.33%, B1: 16.67%, B2: 16.67%} | 3600  |   0
        #       Expense 0     | {A1: 86.67%, A2: 13.33%, B1: 16.67%, B2: 16.67%} |   0   |  2400
        #       Expense 1     | {A1: 25%, A3: 25%}                               | 2400  |   0
        #       Expense 1     | {A1: 25%, A3: 25%}                               |   0   |  1600
        #    Deferral Account | {A1: 62%, A2: 8%, B1: 10%, B2: 10%, A3: 10%}     |   0   |  2000
        #    -------------------------------------------------------------------------------------
        #                                                                        | 6000  |  6000
        expected_analytic_distribution = {
            self.expense_accounts[0].id: {str(aa_a1.id): 86.67, str(aa_a2.id): 13.33, str(aa_b1.id): 16.67, str(aa_b2.id): 16.67},
            self.expense_accounts[1].id: {str(aa_a1.id): 25.0, str(aa_a3.id): 25.0},
            self.deferral_account.id: {str(aa_a1.id): 62.0, str(aa_a2.id): 8.0, str(aa_b1.id): 10.0, str(aa_b2.id): 10.0, str(aa_a3.id): 10.0},
        }
        expected_analytic_amount = [{
            aa_a1.id: (3120.12,     0.00),   # 3600 * 86.67%
            aa_a2.id: ( 479.88,     0.00),   # 3600 * 13.33%
            aa_b1.id: (   0.00,   600.12),   # 3600 * 16.67%
            aa_b2.id: (   0.00,   600.12),   # 3600 * 16.67%
        }, {
            aa_a1.id: (-2080.08,    0.00),   # -2400 * 86.67%
            aa_a2.id: ( -319.92,    0.00),   # -2400 * 13.33%
            aa_b1.id: (    0.00, -400.08),   # -2400 * 16.67%
            aa_b2.id: (    0.00, -400.08),   # -2400 * 16.67%
        },{
            aa_a1.id: (  600.00,    0.00),   # 2400 * 25%
            aa_a3.id: (  600.00,    0.00),   # 2400 * 25%
        },{
            aa_a1.id: ( -400.00,    0.00),   # -1600 * 25%
            aa_a3.id: ( -400.00,    0.00),   # -1600 * 25%
        }, {
            aa_a1.id: (-1240.00,    0.00),   # -2000 * 62%
            aa_a2.id: ( -160.00,    0.00),   # -2000 * 8%
            aa_a3.id: ( -200.00,    0.00),   # -2000 * 10%
            aa_b1.id: (    0.00, -200.00),   # -2000 * 10%
            aa_b2.id: (    0.00, -200.00),   # -2000 * 10%
        }]
        # testing the amount of the analytic lines for the "Grouped Deferral Entry of Aug 2023"
        for index, line in enumerate(generated_entries[0].line_ids):
            self.assertEqual(line.analytic_distribution, expected_analytic_distribution[line.account_id.id])
            for al in line.analytic_line_ids:
                fname_a = analytic_plan_a._column_name()
                fname_b = analytic_plan_b._column_name()
                fname, idx = (fname_a, 0) if al[fname_a] else (fname_b, 1)
                self.assertAlmostEqual(al.amount, expected_analytic_amount[index][al[fname].id][idx])
        # testing the amount of the analytic lines for the "Reversal of Grouped Deferral Entry of Aug 2023"
        # the values should be the opposite of the "Grouped Deferral Entry of Aug 2023"
        for index, line in enumerate(generated_entries[1].line_ids):
            self.assertEqual(line.analytic_distribution, expected_analytic_distribution[line.account_id.id])
            for al in line.analytic_line_ids:
                fname_a = analytic_plan_a._column_name()
                fname_b = analytic_plan_b._column_name()
                fname, idx = (fname_a, 0) if al[fname_a] else (fname_b, 1)
                self.assertAlmostEqual(al.amount, -expected_analytic_amount[index][al[fname].id][idx])

    def test_deferred_revenue_manual_generation_analytic_distribution(self):
        """
        Test if deferred revenues have the right analytic distribution when manually generated.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        move = self.create_invoice(self.revenue_lines)
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Account',
            'plan_id': analytic_plan.id,
        })
        move.invoice_line_ids[0]['analytic_distribution'] = {analytic_account.id: 100}
        options = self.get_options('2023-02-01', '2023-02-28', report=self.deferred_revenue_report)
        options['analytic_accounts'] = [analytic_account.id]
        revenue_handler = self.env['account.deferred.revenue.report.handler']
        deferral_move = self.generate_deferral_entries(options, report_handler=revenue_handler)[0]
        analytic_distributions = deferral_move.line_ids.mapped('analytic_distribution')
        expected_distributions = [{str(analytic_account.id): 100}] * 3
        self.assertEqual(analytic_distributions, expected_distributions)

    def test_deferred_expense_report_invalid_period(self):
        """
        Only periods that start on the first day of a month and end on the last day of a month are allowed.
        """
        self.company.generate_deferred_expense_entries_method = 'manual'
        self.create_invoice([self.expense_lines[0]])

        options = self.get_options('2023-03-01', '2023-03-15')
        lines = self.get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                Total   Not Started   Before   Current   Later
            [    0,                  1,      2,            3,       4,        5     ],
            [
                ('EXP0 Expense 0',   1000,   0,            500,     125,      375   ),
                ('Total',            1000,   0,            500,     125,      375   ),
            ],
            options,
        )

        with self.assertRaisesRegex(UserError, 'You cannot generate entries for a period that does not end at the end of the month.'):
            self.generate_deferral_entries(options)

    def audit_cell(self, options, line, column_name):
        audit_cell_res = self.handler.action_audit_cell(options, {
            'report_line_id': line['id'],
            'calling_line_dict_id': line['id'],
            'expression_label': column_name,
            'column_group_key': next(iter(options['column_groups'])),
        })
        __, account_id = self.deferred_expense_report._get_model_info_from_id(line['id'])
        return self.env['account.move.line']\
                   .search(audit_cell_res['domain'])\
                   .filtered(lambda l: l.account_id.id == account_id)\
                   .sorted(lambda l: (l.date, not l.deferred_start_date, l.id))  # Order by date then Original lines first (False comes before True, so we negate it)

    def get_audited_line_to_assert(self, date, balance):
        return {'date': fields.Date.to_date(date), 'balance': balance}

    def test_deferred_expense_report_audit_cell_on_validation_mode(self):
        """
        Test that the audit correctly works (when clicking on a cell) in the on_validation mode
        Amounts should always correspond between the report and the list view of the audited cell
        """
        self.company.generate_deferred_expense_entries_method = 'on_validation'

        inv1 = self.create_invoice([[self.expense_accounts[0],  1000, '2023-01-01', '2023-04-30']])  # Basic example, 4 full months, in period
        inv2 = self.create_invoice([[self.expense_accounts[0],   100, '2023-04-01', '2023-05-31']])  # 2 full months, Not Started yet
        inv3 = self.create_invoice([
            [self.expense_accounts[0],  10, '2023-01-01', '2023-02-28'],  # 2 full months, fully deferred so shouldn't appear at all
            [self.expense_accounts[0],   1, '2023-01-01', '2023-05-31'],  # 5 full months
        ])
        inv4 = self.create_invoice([
            [self.expense_accounts[0], 10000, '2023-03-01', '2023-04-30'],  # 2 full months
            [self.expense_accounts[0],  1998, '2023-03-01', '2023-03-31'],  # fully inside period -> nothing to defer/show/audit
        ], invoice_date='2023-03-01')
        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)

        # Total column
        audit_lines = self.audit_cell(options, lines[0], 'total')
        self.assertEqual(audit_lines, inv1.invoice_line_ids + inv2.invoice_line_ids + inv3.invoice_line_ids.sorted('id')[1] + inv4.invoice_line_ids.sorted('id')[0])

        # Not Started column
        audit_lines = self.audit_cell(options, lines[0], 'not_started')
        self.assertEqual(audit_lines, inv2.invoice_line_ids)

        # Before March 2023
        audit_lines = self.audit_cell(options, lines[0], 'before').sorted('id')
        self.assertRecordValues(audit_lines, [
        # INV 1
            self.get_audited_line_to_assert('2023-01-01',  1000),    # Original line
            self.get_audited_line_to_assert('2023-01-01', -1000),    # Cancel out original line
            self.get_audited_line_to_assert('2023-01-31',   250),    # Jan 23
            self.get_audited_line_to_assert('2023-02-28',   250),    # Feb 23

        # INV 2: although not started, the original and cancel out should still appear in the "before" column
            self.get_audited_line_to_assert('2023-01-01',   100),    # Original line
            self.get_audited_line_to_assert('2023-01-01',  -100),    # Cancel out original line

        # INV 3, lines are ordred by id, so first the original lines, then the generated lines
        #   self.get_audited_line_to_assert('2023-01-01',    10),   # Original line 1: shouldn't appear because the original line is fully in the past in March
            self.get_audited_line_to_assert('2023-01-01',     1),   # Original line 2
        # However the reversal of line 1 should appear so that it can cancel out with the deferrals created for Jan & Feb 23
            self.get_audited_line_to_assert('2023-01-01',   -10),   # Reversal Original line 1
            self.get_audited_line_to_assert('2023-01-01',    -1),   # Cancel out original line 2
            self.get_audited_line_to_assert('2023-01-31',     5),   # Jan 23 for line 1
            self.get_audited_line_to_assert('2023-02-28',     5),   # Feb 23 for line 1
            self.get_audited_line_to_assert('2023-01-31',     0.2),  # Jan 23 for line 2
            self.get_audited_line_to_assert('2023-02-28',     0.2),  # Feb 23 for line 2
        ])
        # Total = 1000 - 1000 + 250 + 250 + 100 - 100 + 1 - 10 + 5 + 5 - 1 + 0.2 + 0.2 = 500.4 = (2 * 250) + (2 * 0.2) for Jan+Feb 23

        # March 2023
        audit_lines = self.audit_cell(options, lines[0], 'current')
        self.assertRecordValues(audit_lines, [
            self.get_audited_line_to_assert('2023-03-01',  10000),    # inv4 line 1 original
            self.get_audited_line_to_assert('2023-03-01', -10000),    # inv4 line 1 reversal
            self.get_audited_line_to_assert('2023-03-31',    250),    # Amount for inv1
            self.get_audited_line_to_assert('2023-03-31',      0.2),  # Amount for inv3 line 2
            self.get_audited_line_to_assert('2023-03-31',   5000),    # Amount for inv4 line 1
        ])
        # Total = 10000 - 10000 + 5000 + 250 + 0.2 = 5250.2 for March 23

        # Later than March 2023
        audit_lines = self.audit_cell(options, lines[0], 'later')
        self.assertRecordValues(audit_lines, [
            self.get_audited_line_to_assert('2023-04-30',  250),     # Amount for April 23 of Inv 1
            self.get_audited_line_to_assert('2023-04-30',   50),     # Amount for April 23 of Inv 2
            self.get_audited_line_to_assert('2023-04-30',    0.2),   # Amount for April 23 of Inv 3 line 2
            self.get_audited_line_to_assert('2023-04-30', 5000),     # Amount for April 23 of Inv 4 line 1
            self.get_audited_line_to_assert('2023-05-31',   50),     # Amount for May 23 of Inv 2
            self.get_audited_line_to_assert('2023-05-31',    0.2),   # Amount for May 23 of Inv 3 line 2
        ])
        # Total = 250 + 50 + 50 + 0.2 + 0.2 + 5000 = 5350.4 = (1 * 250) + (2 * 50) + (2 * 0.2) + (1 * 5000) for April+May 23

    def test_deferred_expense_report_audit_cell_grouped_mode(self):
        """
        Test that the audit correctly works (when clicking on a cell) in the grouped mode
        If the deferrals haven't been generated yet, the report shows the expected amounts
        which will probably differ from the list view of the audited cell which shows the
        "candidates" lines that are going to be different upon Generating the Entries.
        """

        self.company.generate_deferred_expense_entries_method = 'manual'

        inv1 = self.create_invoice([[self.expense_accounts[0],  1000, '2023-01-01', '2023-04-30']])  # Basic example, 4 full months, in period
        inv2 = self.create_invoice([[self.expense_accounts[0],   100, '2023-04-01', '2023-05-31']])  # 2 full months, Not Started yet
        inv3 = self.create_invoice([
            [self.expense_accounts[0],  10, '2023-01-01', '2023-02-28'],  # 2 full months, fully deferred so shouldn't appear at all
            [self.expense_accounts[0],   1, '2023-01-01', '2023-05-31'],  # 5 full months
        ])
        inv4 = self.create_invoice([
            [self.expense_accounts[0], 10000, '2023-03-01', '2023-04-30'],  # 2 full months
            [self.expense_accounts[0],  1998, '2023-03-01', '2023-03-31'],  # fully inside period -> nothing to defer/show/audit
        ], invoice_date='2023-03-01')
        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)

        # At this point, we haven't generated the entries yet, so we show the candidates lines
        # that will be deferred upon generating the entries (i.e. amounts shown on the reports
        # will be different from the total amounts shown in the list view of the audited cell)

        # Total column
        audit_lines = self.audit_cell(options, lines[0], 'total')
        self.assertEqual(audit_lines, inv1.invoice_line_ids + inv2.invoice_line_ids + inv3.invoice_line_ids.sorted('id')[1] + inv4.invoice_line_ids.sorted('id')[0])

        # Not Started column
        audit_lines = self.audit_cell(options, lines[0], 'not_started')
        self.assertEqual(audit_lines, inv2.invoice_line_ids)

        # Before March 2023 (Jan + Feb)
        audit_lines = self.audit_cell(options, lines[0], 'before')
        self.assertRecordValues(audit_lines, [
            {'id': inv1.invoice_line_ids[0].id},
            {'id': inv3.invoice_line_ids[1].id},
        ])

        # March 2023
        audit_lines = self.audit_cell(options, lines[0], 'current')
        self.assertRecordValues(audit_lines, [
            {'id': inv1.invoice_line_ids[0].id},
            {'id': inv3.invoice_line_ids[1].id},
            {'id': inv4.invoice_line_ids[0].id},
        ])

        # Later than March 2023 (April + May)
        audit_lines = self.audit_cell(options, lines[0], 'later')
        self.assertRecordValues(audit_lines, [
            {'id': inv1.invoice_line_ids.id},
            {'id': inv2.invoice_line_ids.id},
            {'id': inv3.invoice_line_ids.sorted('id')[1].id},
            {'id': inv4.invoice_line_ids.sorted('id')[0].id},
        ])

        # Now, let's generate the entries so that the amounts shown in the report match the
        # totals of the list view of the audited cell. We should generate the entries for the
        # previous periods too to have the correct amounts in the "Before" column.
        for report_date_from, report_date_to in (('2023-01-01', '2023-01-31'), ('2023-02-01', '2023-02-28'), ('2023-03-01', '2023-03-31')):
            self.generate_deferral_entries(self.get_options(report_date_from, report_date_to))
        lines = self.get_lines(options)

        # Total column
        audit_lines = self.audit_cell(options, lines[0], 'total')
        self.assertEqual(audit_lines, inv1.invoice_line_ids + inv2.invoice_line_ids + inv3.invoice_line_ids.sorted('id')[1] + inv4.invoice_line_ids.sorted('id')[0])

        # Not Started column
        audit_lines = self.audit_cell(options, lines[0], 'not_started')
        self.assertEqual(audit_lines, inv2.invoice_line_ids)

        # Before March 2023 (Jan + Feb)
        audit_lines = self.audit_cell(options, lines[0], 'before')
        self.assertRecordValues(audit_lines[:3], [  # Original lines
            {'id': inv1.invoice_line_ids.id},
            {'id': inv2.invoice_line_ids.id},
            {'id': inv3.invoice_line_ids[1].id},
        ])
        self.assertRecordValues(audit_lines[3:], [  # Generated grouping lines
        # Grouped of Jan 23
            self.get_audited_line_to_assert('2023-01-31',  -1111),      # = 1000 + 100 + 10 + 1 for Jan 23  (deferral of 10 is used to compute the grouped deferral of Jan 23)
            self.get_audited_line_to_assert('2023-01-31',    255.2),    # = (1 * 250) + (1 * 5) + (1 * 0.2) for Jan 23
        # Reversal of Jan 23 (on the next day)
            self.get_audited_line_to_assert('2023-02-01',   1111),
            self.get_audited_line_to_assert('2023-02-01',  - 255.2),
        # Grouped of Feb 23
            self.get_audited_line_to_assert('2023-02-28',  -1111),      # same as above
            self.get_audited_line_to_assert('2023-02-28',    510.4),    # = (2 * 250) + (2 * 5) + (2 * 0.2) for Jan + Feb 23
        # Reversal of Feb 23 does not exist in the before period as it is only created on the 1st March
        ])
        # Total = 1000 + 100 + 1 - 1111 + 255.2 + 1111 - 255.2 - 1111 + 510.4 = 500.4 for Jan + Feb 23 = (2 * 250) + (2 * 0.2)

        # March 2023
        audit_lines = self.audit_cell(options, lines[0], 'current')
        self.assertRecordValues(audit_lines, [
            self.get_audited_line_to_assert('2023-03-01',  10000),   # Inv4 line 1 original
        # Reversal of grouped of February
            self.get_audited_line_to_assert('2023-03-01',   1111),   # = 1000 + 100 + 10 + 1 for Feb 23  (deferral of 10 is used to compute the grouped deferral of Feb 23)
            self.get_audited_line_to_assert('2023-03-01', -  510.4),  # = - (2 * 250) - (2 * 5) - (2 * 0.2) for Jan + Feb 23
        # Grouped of current month (March 23)
            self.get_audited_line_to_assert('2023-03-31', -11101),  # Deferral of 10 not included anymore in March
            self.get_audited_line_to_assert('2023-03-31',   5750.6),  # = (3 * 250) + (3 * 0.2)+ (1 * 5000) for Jan + Feb + March 23
        ])
        # Total = 10000 + 1111 - 510.4 - 11101 + 5750.6 = 5250.2 for March 23 = 250 + 0.2 + 5000 OK

        # Later than March 2023 (April + May)
        audit_lines = self.audit_cell(options, lines[0], 'later')
        self.assertRecordValues(audit_lines, [
        # Only the Reversal of previous period exist as we've only generated entries up to March and not after
            self.get_audited_line_to_assert('2023-04-01',  11101),
            self.get_audited_line_to_assert('2023-04-01', - 5750.6),
        ])
        # Total = 11101 - 5750.6 = 5350.2 for April/May = (1 * 250) + (2 * 50) + (2 * 0.2) + (1 * 5000) OK

        # Let's generate for April too (not May as everything is totally deferred in May)
        # Now we'll have to include inv2 too
        self.generate_deferral_entries(self.get_options('2023-04-01', '2023-04-30'))
        audit_lines = self.audit_cell(options, lines[0], 'later')
        self.assertRecordValues(audit_lines, [
        # Reversal of grouped of March
            self.get_audited_line_to_assert('2023-04-01',  11101),
            self.get_audited_line_to_assert('2023-04-01', - 5750.6),
        # Grouped of April
            self.get_audited_line_to_assert('2023-04-30', -11101),
            self.get_audited_line_to_assert('2023-04-30',  11050.8),  # = (4 * 250) + (4 * 0.2) + (1 * 50) + (2 * 5000) for Jan -> April 23
        # Reversal of April
            self.get_audited_line_to_assert('2023-05-01',  11101),
            self.get_audited_line_to_assert('2023-05-01', -11050.8),
        ])
        # Total = Just reversal of grouped of March, so same as previous

        # Now, let's create a new bill such that we have a mix of generated deferrals and candidates
        inv5 = self.create_invoice([[self.expense_accounts[0],  100000, '2023-01-01', '2023-05-31']])

        # Generate deferrals for previous months, but not March 23 yet.
        for report_date_from, report_date_to in (('2023-01-01', '2023-01-31'), ('2023-02-01', '2023-02-28')):
            self.generate_deferral_entries(self.get_options(report_date_from, report_date_to))

        options = self.get_options('2023-03-01', '2023-03-31')
        lines = self.get_lines(options)

        # Total column
        audit_lines = self.audit_cell(options, lines[0], 'total')
        self.assertEqual(audit_lines, inv1.invoice_line_ids + inv2.invoice_line_ids
                         + inv3.invoice_line_ids.sorted('id')[1] + inv4.invoice_line_ids.sorted('id')[0]
                         + inv5.invoice_line_ids)

        # Not Started column
        audit_lines = self.audit_cell(options, lines[0], 'not_started')
        self.assertEqual(audit_lines, inv2.invoice_line_ids)

        # Before March 2023 (Jan + Feb)
        audit_lines = self.audit_cell(options, lines[0], 'before')
        self.assertRecordValues(audit_lines[:4], [  # Original lines
            {'id': inv1.invoice_line_ids.id},
            {'id': inv2.invoice_line_ids.id},
            {'id': inv3.invoice_line_ids[1].id},
            {'id': inv5.invoice_line_ids.id},  # new
        ])
        self.assertRecordValues(audit_lines[4:], [  # Generated grouping lines
        # Grouped of Jan 23
            self.get_audited_line_to_assert('2023-01-31', -   1111),      # inv1,2,3,4 = 1000 + 100 + 10 + 1 for Jan 23  (deferral of 10 is used to compute the grouped deferral of Jan 23)
            self.get_audited_line_to_assert('2023-01-31',      255.2),    # = (1 * 250) + (1 * 5) + (1 * 0.2) for Jan 23
            self.get_audited_line_to_assert('2023-01-31', - 100000),    # just inv5
            self.get_audited_line_to_assert('2023-01-31',    20000),
        # Reversal of Jan 23 (on the next day)
            self.get_audited_line_to_assert('2023-02-01',     1111),
            self.get_audited_line_to_assert('2023-02-01', -    255.2),
            self.get_audited_line_to_assert('2023-02-01',   100000),
            self.get_audited_line_to_assert('2023-02-01', -  20000),
        # Grouped of Feb 23
            self.get_audited_line_to_assert('2023-02-28', -   1111),      # same as above
            self.get_audited_line_to_assert('2023-02-28',      510.4),    # = (2 * 250) + (2 * 5) + (2 * 0.2) for Jan + Feb 23
            self.get_audited_line_to_assert('2023-02-28', - 100000),
            self.get_audited_line_to_assert('2023-02-28',    40000),    # inv5: 2 * 20000 for Jan + Feb 23
        # Reversal of Feb 23 does not exist in the before period as it is only created on the 1st March
        ])
        # Subtotal inv1,2,3 = 1000 + 100 + 1 (originals) - 1111 + 255.2 + 1111 - 255.2 - 1111 + 510.4 = 500.4 for Jan + Feb 23 = (2 * 250) + (2 * 0.2)
        # Subtotal inv4 = 0 as it does not exist yet
        # Subtotal inv5 = 10000 (original) -10000 + 2000 + 10000 - 2000 - 10000 + 4000 = 4000
        # Total = 4000 + 500.4 = 4500.4

        # March 2023
        audit_lines = self.audit_cell(options, lines[0], 'current')
        self.assertRecordValues(audit_lines, [
            self.get_audited_line_to_assert('2023-03-01',   10000),       # Inv4 line 1 original
        # Reversal of grouped of February
            self.get_audited_line_to_assert('2023-03-01',    1111),    # inv1,2,3
            self.get_audited_line_to_assert('2023-03-01', -   510.4),
            self.get_audited_line_to_assert('2023-03-01',  100000),  # inv5
            self.get_audited_line_to_assert('2023-03-01', - 40000),
        # Grouped of current month (March 23)
            self.get_audited_line_to_assert('2023-03-31', - 11101),   # inv1,2,3 + 4
            self.get_audited_line_to_assert('2023-03-31',    5750.6),
            # Nothing for inv5 as we've not yet generated for March since its creation
        ])
        # Total = 10000 + 1111 - 510.4 + 100000 - 40000 - 11101 + 5750.6 = 65 250.2
        # The total of the list view is different from the cell (25 250.2 = inv1 + inv3.1 + inv4 + inv5) so we directly see that
        # there is a problem and the deferrals are not completely generated.
        # The difference is 40 000, so we know that inv5 is not yet generated

        # Generate for March 23
        self.generate_deferral_entries(self.get_options('2023-03-01', '2023-03-31'))

        audit_lines = self.audit_cell(options, lines[0], 'current')
        self.assertRecordValues(audit_lines, [
            self.get_audited_line_to_assert('2023-03-01',    10000),   # Inv4 line 1 original
            # Reversal of grouped of February
            self.get_audited_line_to_assert('2023-03-01',     1111),    # inv1,2,3
            self.get_audited_line_to_assert('2023-03-01', -    510.4),
            self.get_audited_line_to_assert('2023-03-01',   100000),  # inv5
            self.get_audited_line_to_assert('2023-03-01', -  40000),
            # Grouped of current month (March 23)
            self.get_audited_line_to_assert('2023-03-31', -  11101),   # inv1,2,3 + 4
            self.get_audited_line_to_assert('2023-03-31',     5750.6),
            self.get_audited_line_to_assert('2023-03-31', - 100000),  # inv5
            self.get_audited_line_to_assert('2023-03-31',    60000),
        ])
        # Total = 10000 + 1111 - 510.4 + 100000 - 40000 - 11101 + 5750.6 - 100000 + 60000 = 25250.2
        # The total of the list view is now the same as from the cell (25 250.2 = inv1 + inv3.1 + inv4 + inv5)
