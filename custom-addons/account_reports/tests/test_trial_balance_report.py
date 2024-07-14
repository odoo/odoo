# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestTrialBalanceReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2016_1_2',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2016_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_2_1',     'account_id': cls.company_data_2['default_account_payable'].id}),
                (0, 0, {'debit': 0.0,       'credit': 100.0,    'name': '2016_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_1_4',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_1_5',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_1_6',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_1_7',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_1_8',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_1_9',     'account_id': cls.company_data['default_account_expense'].id}),
            ],
        })
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': cls.company_data_2['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'name': '2017_2_1',     'account_id': cls.company_data_2['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'name': '2017_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2017_2.action_post()

        # Archive 'default_journal_bank' to ensure archived entries are not filtered out.
        cls.company_data_2['default_journal_bank'].active = False

        # Deactive all currencies to ensure group_multi_currency is disabled.
        cls.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False

        cls.report = cls.env.ref('account_reports.trial_balance_report')

    # -------------------------------------------------------------------------
    # TESTS: Trial Balance
    # -------------------------------------------------------------------------
    def test_trial_balance_unaffected_earnings_current_fiscal_year(self):
        def invoice_move(date):
            return self.env['account.move'].create({
                'move_type': 'entry',
                'date': fields.Date.from_string(date),
                'journal_id': self.company_data['default_journal_misc'].id,
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                    (0, 0, {'debit': 0.0,    'credit': 3000.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            })

        move_2009_12 = invoice_move('2009-12-31')
        move_2009_12.action_post()

        move_2010_01 = invoice_move('2010-01-31')
        move_2010_01.action_post()

        move_2010_02 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2010-02-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,    'credit': 300.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2010_02.action_post()

        move_2010_03 = invoice_move('2010-03-01')
        move_2010_03.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2010-02-01'), fields.Date.from_string('2010-02-28'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                           [  Initial Balance   ]          [       Balance      ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                ('211000 Account Payable',              2000.0,         0.0,            100.0,          0.0,            2100.0,         0.0),
                ('400000 Product Sales',                0.0,            3000.0,         0.0,            300.0,          0.0,            3300.0),
                ('600000 Expenses',                     2000.0,         0.0,            200.0,          0.0,            2200.0,         0.0),
                ('999999 Undistributed Profits/Losses', 0.0,            1000.0,         0.0,            0.0,            0.0,            1000.0),
                ('Total',                               4000.0,         4000.0,         300.0,          300.0,          4300.0,         4300.0),
            ],
            options,
        )

    def test_trial_balance_unaffected_earnings_previous_fiscal_year(self):
        def invoice_move(date):
            return self.env['account.move'].create({
                'move_type': 'entry',
                'date': fields.Date.from_string(date),
                'journal_id': self.company_data['default_journal_misc'].id,
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                    (0, 0, {'debit': 0.0,    'credit': 3000.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            })

        move_2009_12 = invoice_move('2009-12-31')
        move_2009_12.action_post()

        move_2010_01 = invoice_move('2010-01-31')
        move_2010_01.action_post()

        move_2010_02 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2010-02-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,    'credit': 300.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2010_02.action_post()

        move_2010_03 = invoice_move('2010-03-01')
        move_2010_03.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2010-01-01'), fields.Date.from_string('2010-02-28'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                           [  Initial Balance   ]          [       Balance      ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                ('211000 Account Payable',              1000.0,         0.0,            1100.0,         0.0,            2100.0,         0.0),
                ('400000 Product Sales',                0.0,            0.0,            0.0,            3300.0,         0.0,            3300.0),
                ('600000 Expenses',                     0.0,            0.0,            2200.0,         0.0,            2200.0,         0.0),
                ('999999 Undistributed Profits/Losses', 0.0,            1000.0,         0.0,            0.0,            0.0,            1000.0),
                ('Total',                               1000.0,         1000.0,         3300.0,         3300.0,         4300.0,         4300.0),
            ],
            options,
        )

    def test_trial_balance_whole_report(self):
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                           [  Initial Balance   ]          [       Balance      ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                ('121000 Account Receivable',           0.0,            0.0,            1000.0,         0.0,            1000.0,         0.0),
                ('211000 Account Payable',              100.0,          0.0,            0.0,            0.0,            100.0,          0.0),
                ('211000 Account Payable',              50.0,           0.0,            0.0,            0.0,            50.0,           0.0),
                ('400000 Product Sales',                0.0,            0.0,            20000.0,        0.0,            20000.0,        0.0),
                ('400000 Product Sales',                0.0,            0.0,            0.0,            200.0,          0.0,            200.0),
                ('600000 Expenses',                     0.0,            0.0,            0.0,            21000.0,        0.0,            21000.0),
                ('600000 Expenses',                     0.0,            0.0,            200.0,          0.0,            200.0,          0.0),
                ('999999 Undistributed Profits/Losses', 0.0,            100.0,          0.0,            0.0,            0.0,            100.0),
                ('999999 Undistributed Profits/Losses', 0.0,             50.0,          0.0,            0.0,            0.0,            50.0),
                ('Total',                               150.0,          150.0,          21200.0,        21200.0,        21350.0,        21350.0),
            ],
            options,
        )

    def test_trial_balance_filter_journals(self):
        self.env.companies = self.env.company

        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options = self._update_multi_selector_filter(options, 'journals', self.company_data['default_journal_sale'].ids)

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                           [  Initial Balance   ]          [       Balance      ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                ('121000 Account Receivable',          0.0,            0.0,             1000.0,         0.0,            1000.0,         0.0),
                ('400000 Product Sales',               0.0,            0.0,             20000.0,        0.0,            20000.0,        0.0),
                ('600000 Expenses',                    0.0,            0.0,             0.0,            21000.0,        0.0,             21000.0),
                ('Total',                              0.0,            0.0,             21000.0,        21000.0,        21000.0,         21000.0),
            ],
            options,
        )

    def test_trial_balance_comparisons(self):
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options = self._update_comparison_filter(options, self.report, 'previous_period', 1)

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                           [  Initial Balance   ]          [        2016        ]          [        2017        ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6,              7,              8],
            [
                ('121000 Account Receivable',          0.0,            0.0,             0.0,            0.0,            1000.0,         0.0,            1000.0,         0.0),
                ('211000 Account Payable',             0.0,            0.0,             100.0,          0.0,            0.0,            0.0,            100.0,          0.0),
                ('211000 Account Payable',             0.0,            0.0,             50.0,           0.0,            0.0,            0.0,            50.0,           0.0),
                ('400000 Product Sales',               0.0,            0.0,             0.0,            300.0,          20000.0,        0.0,            19700.0,        0.0),
                ('400000 Product Sales',               0.0,            0.0,             0.0,            50.0,           0.0,            200.0,          0.0,            250.0),
                ('600000 Expenses',                    0.0,            0.0,             200.0,          0.0,            0.0,            21000.0,        0.0,            20800.0),
                ('600000 Expenses',                    0.0,            0.0,             0.0,            0.0,            200.0,          0.0,            200.0,          0.0),
                ('Total',                              0.0,            0.0,             350.0,          350.0,          21200.0,        21200.0,        21050.0,        21050.0),
            ],
            options,
        )

    def test_trial_balance_account_group_with_hole(self):
        """
        Let's say you have the following account groups: 10, 101, 1012
        If you have entries for group 10 and 1012 but none for 101,
        the trial balance report should work correctly

        - 10  --> has entries
          - 101 --> NO ENTRIES
            - 1012 --> has entries

        """

        test_journal = self.env['account.journal'].create({
            'name': 'test journal',
            'code': 'TJ',
            'type': 'general',
        })

        self.env['account.group'].create([
            {'name': 'Group_10', 'code_prefix_start': '10', 'code_prefix_end': '10'},
            {'name': 'Group_101', 'code_prefix_start': '101', 'code_prefix_end': '101'},
            {'name': 'Group_1012', 'code_prefix_start': '1012', 'code_prefix_end': '1012'},
        ])

        # Create the accounts.
        account_a, account_a1 = self.env['account.account'].create([
            {'code': '100000', 'name': 'Account A', 'account_type': 'asset_current'},
            {'code': '101200', 'name': 'Account A1', 'account_type': 'asset_current'},
        ])

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': test_journal.id,
            'line_ids': [
                Command.create({'debit': 100.0,     'credit': 0.0,      'name': 'account_a_1',     'account_id': account_a.id}),
                Command.create({'debit': 0.0,       'credit': 100.0,    'name': 'account_a_2',     'account_id': account_a.id}),
                Command.create({'debit': 200.0,     'credit': 0.0,      'name': 'account_a1_1',    'account_id': account_a1.id}),
                Command.create({'debit': 0.0,       'credit': 200.0,    'name': 'account_a1_2',    'account_id': account_a1.id}),
            ],
        })
        move.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2017-06-01'), fields.Date.from_string('2017-06-01'))
        options = self._update_multi_selector_filter(options, 'journals', test_journal.ids)
        options['unfold_all'] = True

        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                     1,              2,               3,              4,              5,              6],
            [
                ['10 Group_10',                        0.0,            0.0,             300.0,          300.0,          0.0,            0.0],
                ['100000 Account A',                   0.0,            0.0,             100.0,          100.0,          0.0,            0.0],
                ['101 Group_101',                      0.0,            0.0,             200.0,          200.0,          0.0,            0.0],
                ['1012 Group_1012',                    0.0,            0.0,             200.0,          200.0,          0.0,            0.0],
                ['101200 Account A1',                  0.0,            0.0,             200.0,          200.0,          0.0,            0.0],
                ['Total',                              0.0,            0.0,             300.0,          300.0,          0.0,            0.0]
            ],
            options,
        )
