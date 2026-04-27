# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged

from odoo import Command

@tagged('post_install', '-at_install')
class TestCashFlowReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref('account_reports.cash_flow_report')

        cls.misc_journal = cls.company_data['default_journal_misc']
        cls.cash_journal = cls.company_data['default_journal_cash']
        cls.bank_journal = cls.company_data['default_journal_bank']

        cls.account_cash = cls.cash_journal.default_account_id
        cls.account_bank = cls.bank_journal.default_account_id
        cls.account_receivable_1 = cls.company_data['default_account_receivable']
        cls.account_receivable_2 = cls.env['account.account'].create({
            'account_type': 'asset_receivable',
            'name': 'Account Receivable 2',
            'code': '121020',
            'reconcile': True,
        })
        cls.account_receivable_3 = cls.env['account.account'].create({
            'account_type': 'asset_receivable',
            'name': 'Account Receivable 3',
            'code': '121030',
            'reconcile': True,
        })

        cls.account_no_tag = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_no_tag',
            'code': '121040',
            'reconcile': True,
        })
        cls.account_financing = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_financing',
            'code': '121050',
            'reconcile': True,
            'tag_ids': cls.env.ref('account.account_tag_financing'),
        })
        cls.account_operating = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_operating',
            'code': '121060',
            'reconcile': True,
            'tag_ids': cls.env.ref('account.account_tag_operating'),
        })
        cls.account_investing = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_investing',
            'code': '121070',
            'reconcile': True,
            'tag_ids': cls.env.ref('account.account_tag_investing'),
        })

    def _reconcile_on(self, lines, account):
        lines.filtered(lambda line: line.account_id == account and not line.reconciled).reconcile()

    def test_growth_comparison(self):
        """ Enables period comparison and tests the growth comparison column; in order to ensure this feature works on reports with dynamic lines.
        """
        self.report.filter_period_comparison = True
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options = self._update_comparison_filter(options, self.report, 'previous_period', 1)

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-01-01',
            'journal_id': self.misc_journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,     'account_id': self.account_bank.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,     'account_id': self.account_cash.id}),
                (0, 0, {'debit':   0.0,     'credit': 200.0,   'account_id': self.account_no_tag.id}),
            ],
        })
        move_1.action_post()

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.misc_journal.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,     'credit': 0.0,     'account_id': self.account_bank.id}),
                (0, 0, {'debit': 1000.0,     'credit': 0.0,     'account_id': self.account_cash.id}),
                (0, 0, {'debit':   0.0,      'credit': 2000.0,  'account_id': self.account_no_tag.id}),
            ],
        })
        move_2.action_post()

        self.assertColumnPercentComparisonValues(
            self.report._get_lines(options),
            [
                ('Cash and cash equivalents, beginning of period',         'n/a',      'muted'),
                ('Net increase in cash and cash equivalents',              '900.0%',   'green'),
                ('Cash flows from operating activities',                   'n/a',      'muted'),
                ('Advance Payments received from customers',               'n/a',      'muted'),
                ('Cash received from operating activities',                'n/a',      'muted'),
                ('Advance payments made to suppliers',                     'n/a',      'muted'),
                ('Cash paid for operating activities',                     'n/a',      'muted'),
                ('Cash flows from investing & extraordinary activities',   'n/a',      'muted'),
                ('Cash in',                                                'n/a',      'muted'),
                ('Cash out',                                               'n/a',      'muted'),
                ('Cash flows from financing activities',                   'n/a',      'muted'),
                ('Cash in',                                                'n/a',      'muted'),
                ('Cash out',                                               'n/a',      'muted'),
                ('Cash flows from unclassified activities',                '900.0%',   'green'),
                ('Cash in',                                                '900.0%',   'green'),
                ('Cash out',                                               'n/a',      'muted'),
                ('Cash and cash equivalents, closing balance',             '1000.0%',  'green'),
            ]
        )

    def test_cash_flow_journals(self):
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))

        misc_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-07-01',
            'journal_id': self.misc_journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,     'account_id': self.account_bank.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,     'account_id': self.account_cash.id}),
                (0, 0, {'debit':   0.0,     'credit': 200.0,   'account_id': self.account_no_tag.id}),
            ],
        })
        misc_move.action_post()

        bank_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-07-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 200.0,     'credit': 0.0,     'account_id': self.account_bank.id}),
                (0, 0, {'debit':   0.0,     'credit': 200.0,   'account_id': self.account_no_tag.id}),
            ],
        })
        bank_move.action_post()

        cash_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-07-01',
            'journal_id': self.cash_journal.id,
            'line_ids': [
                (0, 0, {'debit': 200.0,     'credit': 0.0,     'account_id': self.account_cash.id}),
                (0, 0, {'debit':   0.0,     'credit': 200.0,   'account_id': self.account_no_tag.id}),
            ],
        })
        cash_move.action_post()

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                         600.0],
            ['Cash flows from operating activities',                                0.0],
            ['Advance Payments received from customers',                            0.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from unclassified activities',                           600.0],
            ['Cash in',                                                           600.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                        600.0],
        ], options)

        # This move should not appear since it does not use a bank or cash account
        receivable_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-07-01',
            'journal_id': self.misc_journal.id,
            'line_ids': [
                (0, 0, {'debit': 200.0,     'credit': 0.0,     'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit':   0.0,     'credit': 200.0,   'account_id': self.account_no_tag.id}),
            ],
        })
        # Default journal account that hasn't "Bank and Cash" or "Credit Card" type should not appear
        self.misc_journal.default_account_id = self.account_no_tag
        receivable_move.action_post()

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                         600.0],
            ['Cash flows from operating activities',                                0.0],
            ['Advance Payments received from customers',                            0.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from unclassified activities',                           600.0],
            ['Cash in',                                                           600.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                        600.0],
        ], options)

    def test_cash_flow_comparison(self):
        self.report.filter_period_comparison = True
        self.report.default_opening_date_filter = 'this_year'

        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options = self._update_comparison_filter(options, self.report, comparison_type='previous_period', number_period=1)
        options['filter_period_comparison'] = True

        # Current period
        invoice_current_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-08',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 230.0,  'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 230.0,  'account_id': self.account_no_tag.id}),
            ],
        })
        invoice_current_period.action_post()

        payment_current_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-16',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
            ],
        })
        payment_current_period.action_post()

        self._reconcile_on((invoice_current_period + payment_current_period).line_ids, self.account_receivable_1)

        # Past period
        invoice_past_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-01-08',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0,  'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 100.0,  'account_id': self.account_no_tag.id}),
            ],
        })
        invoice_past_period.action_post()

        payment_past_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-01-16',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 100.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 100.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
            ],
        })
        payment_past_period.action_post()

        self._reconcile_on((invoice_past_period + payment_past_period).line_ids, self.account_receivable_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1, 2], [
            ['Cash and cash equivalents, beginning of period',            100.0,        0.0],
            ['Net increase in cash and cash equivalents',                 230.0,      100.0],
            ['Cash flows from operating activities',                        0.0,        0.0],
            ['Advance Payments received from customers',                    0.0,        0.0],
            ['Cash received from operating activities',                     0.0,        0.0],
            ['Advance payments made to suppliers',                          0.0,        0.0],
            ['Cash paid for operating activities',                          0.0,        0.0],
            ['Cash flows from investing & extraordinary activities',        0.0,        0.0],
            ['Cash in',                                                     0.0,        0.0],
            ['Cash out',                                                    0.0,        0.0],
            ['Cash flows from financing activities',                        0.0,        0.0],
            ['Cash in',                                                     0.0,        0.0],
            ['Cash out',                                                    0.0,        0.0],
            ['Cash flows from unclassified activities',                   230.0,      100.0],
            ['Cash in',                                                   230.0,      100.0],
            ['Cash out',                                                    0.0,        0.0],
            ['Cash and cash equivalents, closing balance',                330.0,      100.0],
        ], options)

    def test_cash_flow_column_groups(self):
        self.report.filter_period_comparison = True
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-31'))
        options = self._update_comparison_filter(options, self.report, comparison_type='previous_period', number_period=1)
        options['filter_period_comparison'] = True

        invoice_current_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-08',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 1150.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 150.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice_current_period.action_post()

        payment_current_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-16',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
            ],
        })
        payment_current_period.action_post()

        self._reconcile_on((invoice_current_period + payment_current_period).line_ids, self.account_receivable_1)

        invoice_previous_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-12-08',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 575.0, 'credit': 0.0,   'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,   'credit': 75.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice_previous_period.action_post()

        payment_previous_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-12-16',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 115.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 115.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
            ],
        })
        payment_previous_period.action_post()

        self._reconcile_on((invoice_previous_period + payment_previous_period).line_ids, self.account_receivable_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1, 2], [
            ['Cash and cash equivalents, beginning of period',            115.0,        0.0],
            ['Net increase in cash and cash equivalents',                 230.0,      115.0],
            ['Cash flows from operating activities',                      200.0,      100.0],
            ['Advance Payments received from customers',                    0.0,        0.0],
            ['Cash received from operating activities',                   200.0,      100.0],
            ['Advance payments made to suppliers',                          0.0,        0.0],
            ['Cash paid for operating activities',                          0.0,        0.0],
            ['Cash flows from investing & extraordinary activities',        0.0,        0.0],
            ['Cash in',                                                     0.0,        0.0],
            ['Cash out',                                                    0.0,        0.0],
            ['Cash flows from financing activities',                        0.0,        0.0],
            ['Cash in',                                                     0.0,        0.0],
            ['Cash out',                                                    0.0,        0.0],
            ['Cash flows from unclassified activities',                    30.0,       15.0],
            ['Cash in',                                                    30.0,       15.0],
            ['Cash out',                                                    0.0,        0.0],
            ['Cash and cash equivalents, closing balance',                345.0,      115.0],
        ], options)

    def test_cash_flow_multi_company_multi_currency_unfolding(self):
        company_data_3 = self.setup_other_company(name="Company 3")
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))
        options['unfold_all'] = True
        self.company_data_2['default_journal_bank'].default_account_id.code = '101411'

        for company_data in (self.company_data, self.company_data_2, company_data_3):
            account_operating = self.env['account.account'].with_company(company_data['company']).create({
                'account_type': 'asset_current',
                'name': 'Account Operating',
                'code': '121160',
                'reconcile': True,
                'tag_ids': self.env.ref('account.account_tag_operating'),
            })
            invoice = self.env['account.move'].with_company(company_data['company']).create({
                'move_type': 'entry',
                'date': '2016-01-01',
                'journal_id': company_data['default_journal_bank'].id,
                'line_ids': [
                    (0, 0, {'debit': 1150.0, 'credit': 0.0,    'account_id': company_data['default_account_receivable'].id}),
                    (0, 0, {'debit': 0.0,    'credit': 1150.0, 'account_id': account_operating.id}),
                ],
            })
            invoice.action_post()
            payment = self.env['account.move'].with_company(company_data['company']).create({
                'move_type': 'entry',
                'date': '2017-01-01',
                'journal_id': company_data['default_journal_bank'].id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': company_data['default_account_receivable'].id}),
                    (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': company_data['default_journal_bank'].default_account_id.id}),
                ],
            })
            payment.action_post()
            self._reconcile_on((invoice + payment).line_ids, company_data['default_account_receivable'])

        lines = self.report._get_lines(options)
        self.assertLinesValues(lines, [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                           575.0],
            ['Cash flows from operating activities',                                575.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                             575.0],
            ['121160 Account Operating',                                            230.0],  # Company 1
            ['Account Operating',                                                   115.0],  # Company 2 (rate 2.0)
            ['Account Operating',                                                   230.0],  # Company 3
            ['Total Cash received from operating activities',                       575.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                               0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                          575.0],
            ['101401 Bank',                                                         230.0],  # Company 1
            ['101411 Bank',                                                         115.0],  # Company 2 (rate 2.0)
            ['Bank',                                                                230.0],  # Company 3
            ['Total Cash and cash equivalents, closing balance',                    575.0],
        ], options)

    def test_cash_flow_tricky_case_1(self):
        ''' Test how the cash flow report is involved:
         - when reconciling multiple payments.
         - when dealing with multiple receivable lines.
         - when dealing with multiple partials on the same line.
         - When making an advance payment.
         - when adding entries after the report date.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))

        # First invoice, two receivable lines on the same account.
        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 345.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 805.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,   'credit': 150.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 1000.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice.action_post()

        # First payment (20% of the invoice).
        payment_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
            ],
        })
        payment_1.action_post()

        self._reconcile_on((invoice + payment_1).line_ids, self.account_receivable_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                           230.0],
            ['Cash flows from operating activities',                                200.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                             200.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                              30.0],
            ['Cash in',                                                              30.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                          230.0],
        ], options)

        # Second payment (also 20% but will produce two partials, one on each receivable line).
        payment_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-03-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
            ],
        })
        payment_2.action_post()

        self._reconcile_on((invoice + payment_2).line_ids, self.account_receivable_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                           460.0],
            ['Cash flows from operating activities',                                400.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                             400.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                              60.0],
            ['Cash in',                                                              60.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                          460.0],
        ], options)

        # Third payment (residual invoice amount + 1000.0).
        payment_3 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-04-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1690.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 1690.0, 'credit': 0.0,    'account_id': self.account_bank.id}),
            ],
        })
        payment_3.action_post()

        self._reconcile_on((invoice + payment_3).line_ids, self.account_receivable_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          2150.0],
            ['Cash flows from operating activities',                               2000.0],
            ['Advance Payments received from customers',                           1000.0],
            ['Cash received from operating activities',                            1000.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             150.0],
            ['Cash in',                                                             150.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                         2150.0],
        ], options)

        # Second invoice.
        invoice_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2018-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice_2.action_post()

        self._reconcile_on((invoice_2 + payment_3).line_ids, self.account_receivable_1)

        # Exceed the report date, should not affect the report.
        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          2150.0],
            ['Cash flows from operating activities',                               2000.0],
            ['Advance Payments received from customers',                           1000.0],
            ['Cash received from operating activities',                            1000.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             150.0],
            ['Cash in',                                                             150.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                         2150.0],
        ], options)

        options['date']['date_to'] = '2018-01-01'

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          2150.0],
            ['Cash flows from operating activities',                               2000.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                            2000.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             150.0],
            ['Cash in',                                                             150.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                         2150.0],
        ], options)

    def test_cash_flow_tricky_case_2(self):
        ''' Test how the cash flow report is involved:
         - when dealing with multiple receivable account.
         - when making reconciliation involving multiple liquidity moves.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))

        # First liquidity move.
        liquidity_move_1 = self.env['account.move'].create({
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 800.0, 'credit': 0.0,   'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,   'credit': 250.0, 'account_id': self.account_receivable_3.id}),
                (0, 0, {'debit': 0.0,   'credit': 250.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 300.0, 'account_id': self.account_bank.id}),
            ],
        })
        liquidity_move_1.action_post()

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                        -300.0],
            ['Cash flows from operating activities',                             -550.0],
            ['Advance Payments received from customers',                         -550.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from unclassified activities',                           250.0],
            ['Cash in',                                                           250.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                       -300.0],
        ], options)

        # Misc. move to be reconciled at 800 / (1000 + 3000) = 20%.

        misc_move = self.env['account.move'].create({
            'date': '2016-02-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_receivable_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 500.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 4500.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.account_receivable_2.id}),
            ],
        })
        misc_move.action_post()

        self._reconcile_on((misc_move + liquidity_move_1).line_ids, self.account_receivable_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                        -300.0],
            ['Cash flows from operating activities',                             2650.0],
            ['Advance Payments received from customers',                         2650.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                            -3600.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                        -3600.0],
            ['Cash flows from unclassified activities',                           650.0],
            ['Cash in',                                                           650.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                       -300.0],
        ], options)

        # Second liquidity move.

        liquidity_move_2 = self.env['account.move'].create({
            'date': '2016-03-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 3200.0, 'credit': 0.0,    'account_id': self.account_receivable_2.id}),
                (0, 0, {'debit': 200.0,  'credit': 0.0,    'account_id': self.account_receivable_3.id}),
                (0, 0, {'debit': 0.0,    'credit': 400.0,  'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.account_bank.id}),
            ],
        })
        liquidity_move_2.action_post()

        self._reconcile_on((misc_move + liquidity_move_2).line_ids, self.account_receivable_2)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                       -3300.0],
            ['Cash flows from operating activities',                             -150.0],
            ['Advance Payments received from customers',                         -150.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                            -3875.0],
            ['Cash in',                                                           400.0],
            ['Cash out',                                                        -4275.0],
            ['Cash flows from unclassified activities',                           725.0],
            ['Cash in',                                                           725.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                      -3300.0],
        ], options)

        # This should not change the report.
        self._reconcile_on((liquidity_move_1 + liquidity_move_2).line_ids, self.account_receivable_3)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                      0.0],
            ['Net increase in cash and cash equivalents',                       -3300.0],
            ['Cash flows from operating activities',                             -150.0],
            ['Advance Payments received from customers',                         -150.0],
            ['Cash received from operating activities',                             0.0],
            ['Advance payments made to suppliers',                                  0.0],
            ['Cash paid for operating activities',                                  0.0],
            ['Cash flows from investing & extraordinary activities',                0.0],
            ['Cash in',                                                             0.0],
            ['Cash out',                                                            0.0],
            ['Cash flows from financing activities',                            -3875.0],
            ['Cash in',                                                           400.0],
            ['Cash out',                                                        -4275.0],
            ['Cash flows from unclassified activities',                           725.0],
            ['Cash in',                                                           725.0],
            ['Cash out',                                                            0.0],
            ['Cash and cash equivalents, closing balance',                      -3300.0],
        ], options)

    def test_cash_flow_tricky_case_3(self):
        ''' Test how the cash flow report is involved:
         - when reconciling entries on a not-receivable/payable account.
         - when dealing with weird liquidity moves.
        '''
        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
                (0, 0, {'debit': 0.0,    'credit': 500.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 500.0, 'account_id': self.account_financing.id}),
            ],
        })

        move_3 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_bank.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })
        (move_1 + move_2 + move_3).action_post()

        # Reconcile everything on account_financing.
        self._reconcile_on((move_1 + move_2 + move_3).line_ids, self.account_financing)

        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          1000.0],
            ['Cash flows from operating activities',                                  0.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                500.0],
            ['Cash in',                                                             500.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             500.0],
            ['Cash in',                                                             500.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                         1000.0],
        ], options)

        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-02-01'))

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                           500.0],
            ['Cash flows from operating activities',                                  0.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             500.0],
            ['Cash in',                                                             500.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                          500.0],
        ], options)

    def test_cash_flow_tricky_case_4(self):
        ''' The difficulty of this case is the liquidity move will pay the misc move at 1000 / 3000 = 1/3.
        However, you must take care of the sign because the 3000 in credit must become 1000 in debit.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 5000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_bank.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
            ],
        })

        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids.filtered('credit') + move_2.line_ids, self.account_financing)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                         -1000.0],
            ['Cash flows from operating activities',                                  0.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                           -1000.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                          -1000.0],
            ['Cash and cash equivalents, closing balance',                        -1000.0],
        ], options)

    def test_cash_flow_tricky_case_5(self):
        ''' Same as test_cash_flow_tricky_case_4 in credit.'''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 3000.0, 'credit': 0.0,    'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,    'credit': 5000.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_bank.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
            ],
        })

        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids.filtered('debit') + move_2.line_ids, self.account_financing)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          1000.0],
            ['Cash flows from operating activities',                                  0.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                            1000.0],
            ['Cash in',                                                            1000.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                         1000.0],
        ], options)

    def test_cash_flow_tricky_case_6(self):
        ''' Test the additional lines on liquidity moves (e.g. bank fees) are well reported. '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        moves = self.env['account.move'].create([
            {
                'date': '2016-01-01',
                'journal_id': self.bank_journal.id,
                'line_ids': [
                    (0, 0, {'debit': 3000.0, 'credit': 0.0,    'account_id': self.account_bank.id}),
                    (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_investing.id}),
                    (0, 0, {'debit': 0.0,    'credit': 2000.0, 'account_id': self.account_receivable_2.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.bank_journal.id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.account_bank.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_no_tag.id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.bank_journal.id,
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_bank.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_no_tag.id}),
                    (0, 0, {'debit': 0.0,    'credit': 2000.0, 'account_id': self.account_receivable_2.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.bank_journal.id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_bank.id}),
                    (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_investing.id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.bank_journal.id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,    'credit': 4000.0, 'account_id': self.account_receivable_1.id}),
                    (0, 0, {'debit': 4000.0, 'credit': 0.0,    'account_id': self.account_receivable_2.id}),
                ],
            },
        ])

        moves.action_post()

        self._reconcile_on(moves.line_ids, self.account_receivable_1)
        self._reconcile_on(moves.line_ids, self.account_receivable_2)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                             0.0],
            ['Cash flows from operating activities',                                  0.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',               2000.0],
            ['Cash in',                                                            2000.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                           -2000.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                          -2000.0],
            ['Cash and cash equivalents, closing balance',                            0.0],
        ], options)

    def test_cash_flow_tricky_case_7(self):
        ''' Test cross reconciliation between liquidity moves with additional lines when the liquidity account
        is reconcile.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 3000.0, 'credit': 0.0,    'account_id': self.account_bank.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 2000.0, 'account_id': self.account_receivable_2.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1500.0, 'account_id': self.account_bank.id}),
                (0, 0, {'debit': 500.0,  'credit': 0.0,    'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_receivable_1.id}),
            ],
        })
        (move_1 + move_2).action_post()

        self.account_bank.reconcile = True

        self._reconcile_on((move_1 + move_2).line_ids, self.account_bank)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          1500.0],
            ['Cash flows from operating activities',                               1000.0],
            ['Advance Payments received from customers',                           1000.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                               1000.0],
            ['Cash in',                                                            1000.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                            -500.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                           -500.0],
            ['Cash and cash equivalents, closing balance',                         1500.0],
        ], options)

    def test_cash_flow_tricky_case_8(self):
        ''' Difficulties on this test are:
        - The liquidity moves are reconciled to move having a total amount of 0.0.
        - Double reconciliation between the liquidity and the misc moves.
        - The reconciliations are partials.
        - There are additional lines on the misc moves.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 100.0, 'account_id': self.account_bank.id}),
                (0, 0, {'debit': 900.0, 'credit': 0.0,   'account_id': self.account_receivable_2.id}),
                (0, 0, {'debit': 0.0,   'credit': 400.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 400.0, 'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_financing.id}),
            ],
        })
        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('debit'), self.account_no_tag)
        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('debit'), self.account_financing)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                          -100.0],
            ['Cash flows from operating activities',                               -900.0],
            ['Advance Payments received from customers',                           -900.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                400.0],
            ['Cash in',                                                             400.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             400.0],
            ['Cash in',                                                             400.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                         -100.0],
        ], options)

    def test_cash_flow_tricky_case_9(self):
        ''' Same as test_cash_flow_tricky_case_8 with reversed debit/credit.'''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0,   'account_id': self.account_bank.id}),
                (0, 0, {'debit': 0.0,   'credit': 900.0, 'account_id': self.account_receivable_2.id}),
                (0, 0, {'debit': 400.0, 'credit': 0.0,   'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 400.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })
        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('credit'), self.account_no_tag)
        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('credit'), self.account_financing)

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                           100.0],
            ['Cash flows from operating activities',                                900.0],
            ['Advance Payments received from customers',                            900.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                               -400.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                           -400.0],
            ['Cash flows from unclassified activities',                            -400.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                           -400.0],
            ['Cash and cash equivalents, closing balance',                          100.0],
        ], options)

    def test_cash_flow_handle_multiple_tags(self):
        ''' Ensure that the balances are correct in the following situations:
            - when several non-cash-flow-report account tags are set
            - when a mix of several non-cash-flow-report tags and one cash-flow report tag are set.
        '''

        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        unrelated_tag_1 = self.env['account.account.tag'].create({
            'name': 'Unrelated Tag 1',
            'applicability': 'accounts',
        })
        unrelated_tag_2 = self.env['account.account.tag'].create({
            'name': 'Unrelated Tag 2',
            'applicability': 'accounts',
        })

        # account_no_tag will now have 2 tags unrelated to the Cash Flow Report.
        # account_financing will now have the `account.account_tag_financing` tag, plus the two unrelated tags.
        (self.account_no_tag + self.account_financing).write({
            'tag_ids': [Command.link(unrelated_tag_1.id), Command.link(unrelated_tag_2.id)],
        })

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 800.0, 'credit':   0.0, 'account_id': self.account_bank.id}),
                (0, 0, {'debit':   0.0, 'credit': 300.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit':   0.0, 'credit': 500.0, 'account_id': self.account_financing.id}),
            ],
        })

        move.action_post()

        self.assertLinesValues(self.report._get_lines(options), [0, 1], [
            ['Cash and cash equivalents, beginning of period',                        0.0],
            ['Net increase in cash and cash equivalents',                           800.0],
            ['Cash flows from operating activities',                                  0.0],
            ['Advance Payments received from customers',                              0.0],
            ['Cash received from operating activities',                               0.0],
            ['Advance payments made to suppliers',                                    0.0],
            ['Cash paid for operating activities',                                    0.0],
            ['Cash flows from investing & extraordinary activities',                  0.0],
            ['Cash in',                                                               0.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from financing activities',                                500.0],
            ['Cash in',                                                             500.0],
            ['Cash out',                                                              0.0],
            ['Cash flows from unclassified activities',                             300.0],
            ['Cash in',                                                             300.0],
            ['Cash out',                                                              0.0],
            ['Cash and cash equivalents, closing balance',                          800.0],
        ], options)

    def test_cash_flow_hierarchy(self):
        """ Test the 'hierarchy' option. I.e. we want to ensure that each section of the report (e.g. "Cash and cash equivalents, beginning of period" and "Cash and cash equivalents, closing balance") has its own dedicated hierarchy and they are not mixed up together.
        """
        options = self._generate_options(self.report, '2016-01-01', '2016-12-31')
        self.env.company.totals_below_sections = True

        # Create the account groups for the bank and cash accounts
        self.env['account.group'].create([
            {'name': 'Group Bank & Cash',   'code_prefix_start': '10',   'code_prefix_end': '10'},
            {'name': 'Group Bank',          'code_prefix_start': '1014', 'code_prefix_end': '1014'},
            {'name': 'Group Cash',          'code_prefix_start': '1015', 'code_prefix_end': '1015'},
        ])
        self.account_bank.code = "10140499"
        self.account_cash.code = "10150199"

        # Create opening balance
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-01-01',
            'journal_id': self.misc_journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit':   0.0,   'account_id': self.account_bank.id}),
                (0, 0, {'debit':  50.0,     'credit':   0.0,   'account_id': self.account_cash.id}),
                (0, 0, {'debit':   0.0,     'credit': 150.0,   'account_id': self.account_no_tag.id}),
            ],
        }).action_post()

        # Test the report with the hierarchy option disabled
        # To make sure that the lines are in the right place we also check their 'level'
        options['hierarchy'] = False
        lines_wo_hierarchy = [
            {
                'name': line['name'],
                'level': line['level'],
                'book_value': line['columns'][-1]['name']
            }
            for line in self.report._get_lines(options)
        ]
        expected_values_wo_hierarchy = [
            {'name': "Cash and cash equivalents, beginning of period",            'level': 0,    'book_value': '$\xa0150.00'},
              {'name': "10140499 Bank",                                           'level': 1,    'book_value': '$\xa0100.00'},
              {'name': "10150199 Cash",                                           'level': 1,    'book_value': '$\xa050.00'},
              {'name': "Total Cash and cash equivalents, beginning of period",    'level': 1,    'book_value': '$\xa0150.00'},
            {'name': "Net increase in cash and cash equivalents",                 'level': 0,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from operating activities",                  'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Advance Payments received from customers",            'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash received from operating activities",             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Advance payments made to suppliers",                  'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash paid for operating activities",                  'level': 4,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from investing & extraordinary activities",  'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Cash in",                                             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash out",                                            'level': 4,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from financing activities",                  'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Cash in",                                             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash out",                                            'level': 4,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from unclassified activities",               'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Cash in",                                             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash out",                                            'level': 4,    'book_value': '$\xa00.00'},
            {'name': "Cash and cash equivalents, closing balance",                'level': 0,    'book_value': '$\xa0150.00'},
              {'name': "10140499 Bank",                                           'level': 1,    'book_value': '$\xa0100.00'},
              {'name': "10150199 Cash",                                           'level': 1,    'book_value': '$\xa050.00'},
              {'name': "Total Cash and cash equivalents, closing balance",        'level': 1,    'book_value': '$\xa0150.00'}
        ]
        # assertEqual is used and not assertLinesValues because we want to check the 'level'
        self.assertEqual(len(lines_wo_hierarchy), len(expected_values_wo_hierarchy))
        self.assertEqual(lines_wo_hierarchy, expected_values_wo_hierarchy)

        # Test the report with the hierarchy option enabled
        # To make sure that the lines are in the right place we also check their 'level'
        options['hierarchy'] = True
        lines = [
            {
                'name': line['name'],
                'level': line['level'],
                'book_value': line['columns'][-1]['name']
            }
            for line in self.report._get_lines(options)
        ]
        expected_values = [
            {'name': "Cash and cash equivalents, beginning of period",            'level': 0,    'book_value': '$\xa0150.00'},
              {'name': "10 Group Bank & Cash",                                    'level': 1,    'book_value': '$\xa0150.00'},
                {'name': "1014 Group Bank",                                       'level': 2,    'book_value': '$\xa0100.00'},
                  {'name': "10140499 Bank",                                       'level': 3,    'book_value': '$\xa0100.00'},
                {'name': "Total 1014 Group Bank",                                 'level': 2,    'book_value': '$\xa0100.00'},
                {'name': "1015 Group Cash",                                       'level': 2,    'book_value': '$\xa050.00'},
                  {'name': "10150199 Cash",                                       'level': 3,    'book_value': '$\xa050.00'},
                {'name': "Total 1015 Group Cash",                                 'level': 2,    'book_value': '$\xa050.00'},
              {'name': "Total 10 Group Bank & Cash",                              'level': 1,    'book_value': '$\xa0150.00'},
            {'name': "Total Cash and cash equivalents, beginning of period",      'level': 1,    'book_value': '$\xa0150.00'},
            {'name': "Net increase in cash and cash equivalents",                 'level': 0,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from operating activities",                  'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Advance Payments received from customers",            'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash received from operating activities",             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Advance payments made to suppliers",                  'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash paid for operating activities",                  'level': 4,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from investing & extraordinary activities",  'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Cash in",                                             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash out",                                            'level': 4,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from financing activities",                  'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Cash in",                                             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash out",                                            'level': 4,    'book_value': '$\xa00.00'},
                {'name': "Cash flows from unclassified activities",               'level': 2,    'book_value': '$\xa00.00'},
                  {'name': "Cash in",                                             'level': 4,    'book_value': '$\xa00.00'},
                  {'name': "Cash out",                                            'level': 4,    'book_value': '$\xa00.00'},
            {'name': "Cash and cash equivalents, closing balance",                'level': 0,    'book_value': '$\xa0150.00'},
              {'name': "10 Group Bank & Cash",                                    'level': 1,    'book_value': '$\xa0150.00'},
                {'name': "1014 Group Bank",                                       'level': 2,    'book_value': '$\xa0100.00'},
                  {'name': "10140499 Bank",                                       'level': 3,    'book_value': '$\xa0100.00'},
                {'name': "Total 1014 Group Bank",                                 'level': 2,    'book_value': '$\xa0100.00'},
                {'name': "1015 Group Cash",                                       'level': 2,    'book_value': '$\xa050.00'},
                  {'name': "10150199 Cash",                                       'level': 3,    'book_value': '$\xa050.00'},
                {'name': "Total 1015 Group Cash",                                 'level': 2,    'book_value': '$\xa050.00'},
              {'name': "Total 10 Group Bank & Cash",                              'level': 1,    'book_value': '$\xa0150.00'},
            {'name': "Total Cash and cash equivalents, closing balance",          'level': 1,    'book_value': '$\xa0150.00'}
        ]
        # assertEqual is used and not assertLinesValues because we want to check the 'level'
        self.assertEqual(len(lines), len(expected_values))
        self.assertEqual(lines, expected_values)
