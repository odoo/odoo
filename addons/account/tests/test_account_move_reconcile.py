# -*- coding: utf-8 -*-
# pylint: disable=C0326
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountMoveReconcile(AccountTestInvoicingCommon):
    ''' Tests about the account.partial.reconcile model, not the reconciliation itself but mainly the computation of
    the residual amounts on account.move.line.
    '''

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.extra_receivable_account_1 = cls.copy_account(cls.company_data['default_account_receivable'])
        cls.extra_receivable_account_2 = cls.copy_account(cls.company_data['default_account_receivable'])
        cls.extra_payable_account_1 = cls.copy_account(cls.company_data['default_account_payable'])
        cls.extra_payable_account_2 = cls.copy_account(cls.company_data['default_account_payable'])

        # ==== Multi-currency setup ====

        cls.currency_data_2 = cls.setup_multi_currency_data(default_values={
            'name': 'Diamond',
            'symbol': '💎',
            'currency_unit_label': 'Diamond',
            'currency_subunit_label': 'Carbon',
        }, rate2016=6.0, rate2017=4.0)

        # ==== Cash Basis Taxes setup ====

        cls.cash_basis_base_account = cls.env['account.account'].create({
            'code': 'cash_basis_base_account',
            'name': 'cash_basis_base_account',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'company_id': cls.company_data['company'].id,
        })
        cls.company_data['company'].account_cash_basis_base_account_id = cls.cash_basis_base_account

        cls.cash_basis_transfer_account = cls.env['account.account'].create({
            'code': 'cash_basis_transfer_account',
            'name': 'cash_basis_transfer_account',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_1 = cls.env['account.account'].create({
            'code': 'tax_account_1',
            'name': 'tax_account_1',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_2 = cls.env['account.account'].create({
            'code': 'tax_account_2',
            'name': 'tax_account_2',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'company_id': cls.company_data['company'].id,
        })

        cls.fake_country = cls.env['res.country'].create({
            'name': "The Island of the Fly",
            'code': 'YY',
        })

        cls.tax_tags = cls.env['account.account.tag'].create({
            'name': 'tax_tag_%s' % str(i),
            'applicability': 'taxes',
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
        } for i in range(8))

        cls.cash_basis_tax_a_third_amount = cls.env['account.tax'].create({
            'name': 'tax_1',
            'amount': 33.3333,
            'company_id': cls.company_data['company'].id,
            'cash_basis_transition_account_id': cls.cash_basis_transfer_account.id,
            'tax_exigibility': 'on_payment',
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[0].ids)],
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_1.id,
                    'tag_ids': [(6, 0, cls.tax_tags[1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[2].ids)],
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_1.id,
                    'tag_ids': [(6, 0, cls.tax_tags[3].ids)],
                }),
            ],
        })

        cls.cash_basis_tax_tiny_amount = cls.env['account.tax'].create({
            'name': 'cash_basis_tax_tiny_amount',
            'amount': 0.0001,
            'company_id': cls.company_data['company'].id,
            'cash_basis_transition_account_id': cls.cash_basis_transfer_account.id,
            'tax_exigibility': 'on_payment',
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[4].ids)],
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_2.id,
                    'tag_ids': [(6, 0, cls.tax_tags[5].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[6].ids)],
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_2.id,
                    'tag_ids': [(6, 0, cls.tax_tags[7].ids)],
                }),
            ],
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def assertFullReconcile(self, full_reconcile, lines):
        exchange_difference_move = full_reconcile.exchange_move_id
        partials = lines.mapped('matched_debit_ids') + lines.mapped('matched_credit_ids')

        if full_reconcile.exchange_move_id:
            lines += exchange_difference_move.line_ids.filtered(lambda line: line.account_id == lines[0].account_id)

        # Use sets to not depend of the order.
        self.assertEqual(set(full_reconcile.partial_reconcile_ids), set(partials))
        self.assertEqual(set(full_reconcile.reconciled_line_ids), set(lines))

        # Ensure there is no residual amount left.
        self.assertRecordValues(lines, [{
            'amount_residual': 0.0,
            'amount_residual_currency': 0.0,
            'reconciled': bool(line.account_id.reconcile),
        } for line in lines])

    def assertPartialReconcile(self, partials, expected_vals_list):
        partials = partials.sorted(lambda part: (
            part.amount,
            part.debit_amount_currency,
            part.credit_amount_currency,
        ))
        self.assertRecordValues(partials, expected_vals_list)

    def assertAmountsGroupByAccount(self, amount_per_account):
        expected_values = {account.id: (account, balance, amount_currency) for account, balance, amount_currency in amount_per_account}

        if not expected_values:
            return

        self.cr.execute('''
            SELECT
                line.account_id,
                COALESCE(SUM(line.balance), 0.0)            AS total_balance,
                COALESCE(SUM(line.amount_currency), 0.0)    AS total_amount_currency
            FROM account_move_line line
            WHERE line.account_id IN %s
            GROUP BY line.account_id
        ''', [tuple(expected_values.keys())])
        for account_id, total_balance, total_amount_currency in self.cr.fetchall():
            account, expected_balance, expected_amount_currency = expected_values[account_id]
            self.assertEqual(
                total_balance,
                expected_balance,
                "Balance of %s is incorrect" % account.name,
            )
            self.assertEqual(
                total_amount_currency,
                expected_amount_currency,
                "Amount currency of %s is incorrect" % account.name,
            )

    # -------------------------------------------------------------------------
    # Test creation of account.partial.reconcile/account.full.reconcile
    # during the reconciliation.
    # -------------------------------------------------------------------------

    def test_reconcile_single_currency(self):
        account_id = self.company_data['default_account_receivable'].id

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'account_id': account_id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': account_id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'account_id': account_id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'account_id': account_id}),
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'account_id': account_id}),
            ]
        })
        move.action_post()

        line_1 = move.line_ids.filtered(lambda line: line.debit == 1000.0)
        line_2 = move.line_ids.filtered(lambda line: line.debit == 200.0)
        line_3 = move.line_ids.filtered(lambda line: line.credit == 300.0)
        line_4 = move.line_ids.filtered(lambda line: line.credit == 400.0)
        line_5 = move.line_ids.filtered(lambda line: line.credit == 500.0)

        self.assertRecordValues(line_1 + line_2 + line_3 + line_4 + line_5, [
            {'amount_residual': 1000.0,     'amount_residual_currency': 1000.0, 'reconciled': False},
            {'amount_residual': 200.0,      'amount_residual_currency': 200.0,  'reconciled': False},
            {'amount_residual': -300.0,     'amount_residual_currency': -300.0, 'reconciled': False},
            {'amount_residual': -400.0,     'amount_residual_currency': -400.0, 'reconciled': False},
            {'amount_residual': -500.0,     'amount_residual_currency': -500.0, 'reconciled': False},
        ])

        res = (line_1 + line_3).reconcile()

        self.assertPartialReconcile(res['partials'], [{
            'amount': 300.0,
            'debit_amount_currency': 300.0,
            'credit_amount_currency': 300.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_3.id,
        }])

        self.assertRecordValues(line_1 + line_3, [
            {'amount_residual': 700.0,      'amount_residual_currency': 700.0,  'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

        res = (line_1 + line_4).reconcile()

        self.assertPartialReconcile(res['partials'], [{
            'amount': 400.0,
            'debit_amount_currency': 400.0,
            'credit_amount_currency': 400.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_4.id,
        }])

        self.assertRecordValues(line_1 + line_4, [
            {'amount_residual': 300.0,      'amount_residual_currency': 300.0,  'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

        res = (line_1 + line_5).reconcile()

        self.assertPartialReconcile(res['partials'], [{
            'amount': 300.0,
            'debit_amount_currency': 300.0,
            'credit_amount_currency': 300.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_5.id,
        }])

        self.assertRecordValues(line_1 + line_5, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -200.0,     'amount_residual_currency': -200.0, 'reconciled': False},
        ])

        res = (line_2 + line_5).reconcile()

        self.assertPartialReconcile(res['partials'], [{
            'amount': 200.0,
            'debit_amount_currency': 200.0,
            'credit_amount_currency': 200.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_5.id,
        }])

        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertFullReconcile(res['full_reconcile'], line_1 + line_2 + line_3 + line_4 + line_5)

    def test_reconcile_same_foreign_currency(self):
        account_id = self.company_data['default_account_receivable'].id

        # Rate is 3.0 in 2016, 2.0 in 2017.
        currency_id = self.currency_data['currency'].id

        moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2016-01-01',
                'line_ids': [
                    (0, 0, {'debit': 1200.0,    'credit': 0.0,      'amount_currency': 3600.0,  'account_id': account_id,   'currency_id': currency_id}),
                    (0, 0, {'debit': 120.0,     'credit': 0.0,      'amount_currency': 360.0,   'account_id': account_id,   'currency_id': currency_id}),

                    (0, 0, {'debit': 0.0,       'credit': 1320.0,                               'account_id': account_id}),
                ]
            },
            {
                'move_type': 'entry',
                'date': '2017-01-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0,       'credit': 240.0,    'amount_currency': -480.0,  'account_id': account_id,   'currency_id': currency_id}),
                    (0, 0, {'debit': 0.0,       'credit': 720.0,    'amount_currency': -1440.0, 'account_id': account_id,   'currency_id': currency_id}),
                    (0, 0, {'debit': 0.0,       'credit': 1020.0,   'amount_currency': -2040.0, 'account_id': account_id,   'currency_id': currency_id}),

                    (0, 0, {'debit': 1980.0,    'credit': 0.0,                                  'account_id': account_id}),
                ]
            }
        ])

        moves.action_post()

        line_1 = moves.line_ids.filtered(lambda line: line.debit == 1200.0)
        line_2 = moves.line_ids.filtered(lambda line: line.debit == 120.0)
        line_3 = moves.line_ids.filtered(lambda line: line.credit == 240.0)
        line_4 = moves.line_ids.filtered(lambda line: line.credit == 720.0)
        line_5 = moves.line_ids.filtered(lambda line: line.credit == 1020.0)

        self.assertRecordValues(line_1 + line_2 + line_3 + line_4 + line_5, [
            {'amount_residual': 1200.0,     'amount_residual_currency': 3600.0,     'reconciled': False},
            {'amount_residual': 120.0,      'amount_residual_currency': 360.0,      'reconciled': False},
            {'amount_residual': -240.0,     'amount_residual_currency': -480.0,     'reconciled': False},
            {'amount_residual': -720.0,     'amount_residual_currency': -1440.0,    'reconciled': False},
            {'amount_residual': -1020.0,    'amount_residual_currency': -2040.0,    'reconciled': False},
        ])

        res = (line_1 + line_3 + line_4).reconcile()

        self.assertPartialReconcile(res['partials'], [
            # Partial generated when reconciling line_1 & line_3:
            {
                'amount': 240.0,
                'debit_amount_currency': 480.0,
                'credit_amount_currency': 480.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_3.id,
            },
            # Partial generated when reconciling line_1 & line_4:
            {
                'amount': 720.0,
                'debit_amount_currency': 1440.0,
                'credit_amount_currency': 1440.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_4.id,
            },
        ])

        self.assertRecordValues(line_1 + line_3 + line_4, [
            {'amount_residual': 240.0,      'amount_residual_currency': 1680.0,     'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        res = (line_1 + line_5).reconcile()

        self.assertPartialReconcile(res['partials'], [{
            'amount': 240.0,
            'debit_amount_currency': 1680.0,
            'credit_amount_currency': 1680.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_5.id,
        }])

        self.assertRecordValues(line_1 + line_5, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': -780.0,     'amount_residual_currency': -360.0,     'reconciled': False},
        ])

        res = (line_2 + line_5).reconcile()

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids.sorted(lambda line: (line.currency_id, abs(line.amount_currency), -line.amount_currency))

        self.assertRecordValues(exchange_diff_lines, [
            # Fix line_2:
            {
                'debit': 660.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency_id,
                'account_id': account_id,
            },
            {
                'debit': 0.0,
                'credit': 660.0,
                'amount_currency': 0.0,
                'currency_id': currency_id,
                'account_id': exchange_diff.journal_id.company_id.income_currency_exchange_account_id.id,
            },
        ])

        self.assertPartialReconcile(res['partials'], [
            # Partial generated when reconciling line_2 & line_5:
            {
                'amount': 120.0,
                'debit_amount_currency': 360.0,
                'credit_amount_currency': 360.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_5.id,
            },
            # Partial fixing line_4 (exchange difference):
            {
                'amount': 660.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': exchange_diff_lines[0].id,
                'credit_move_id': line_5.id,
            },
        ])

        self.assertFullReconcile(res['full_reconcile'], line_1 + line_2 + line_3 + line_4 + line_5)

    def test_reconcile_multiple_currencies(self):
        account_id = self.company_data['default_account_receivable'].id

        # Rate is 3.0 in 2016, 2.0 in 2017.
        currency1_id = self.currency_data['currency'].id
        # Rate is 6.0 in 2016, 4.0 in 2017.
        currency2_id = self.currency_data_2['currency'].id

        moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2016-01-01',
                'line_ids': [
                    (0, 0, {'debit': 1200.0,    'credit': 0.0,      'amount_currency': 3600.0,  'account_id': account_id,   'currency_id': currency1_id}),
                    (0, 0, {'debit': 780.0,     'credit': 0.0,      'amount_currency': 2340.0,  'account_id': account_id,   'currency_id': currency1_id}),

                    (0, 0, {'debit': 0.0,       'credit': 1980.0,                               'account_id': account_id}),
                ]
            },
            {
                'move_type': 'entry',
                'date': '2017-01-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0,       'credit': 240.0,    'amount_currency': -960.0,  'account_id': account_id,   'currency_id': currency2_id}),
                    (0, 0, {'debit': 0.0,       'credit': 720.0,    'amount_currency': -2880.0, 'account_id': account_id,   'currency_id': currency2_id}),
                    (0, 0, {'debit': 0.0,       'credit': 1020.0,   'amount_currency': -4080.0, 'account_id': account_id,   'currency_id': currency2_id}),

                    (0, 0, {'debit': 1980.0,    'credit': 0.0,                                  'account_id': account_id}),
                ]
            }
        ])

        moves.action_post()

        line_1 = moves.line_ids.filtered(lambda line: line.debit == 1200.0)
        line_2 = moves.line_ids.filtered(lambda line: line.debit == 780.0)
        line_3 = moves.line_ids.filtered(lambda line: line.credit == 240.0)
        line_4 = moves.line_ids.filtered(lambda line: line.credit == 720.0)
        line_5 = moves.line_ids.filtered(lambda line: line.credit == 1020.0)

        self.assertRecordValues(line_1 + line_2 + line_3 + line_4 + line_5, [
            {'amount_residual': 1200.0,     'amount_residual_currency': 3600.0,     'reconciled': False},
            {'amount_residual': 780.0,      'amount_residual_currency': 2340.0,     'reconciled': False},
            {'amount_residual': -240.0,     'amount_residual_currency': -960.0,     'reconciled': False},
            {'amount_residual': -720.0,     'amount_residual_currency': -2880.0,    'reconciled': False},
            {'amount_residual': -1020.0,    'amount_residual_currency': -4080.0,    'reconciled': False},
        ])

        res = (line_1 + line_3 + line_4).reconcile()

        self.assertPartialReconcile(res['partials'], [
            # Partial generated when reconciling line_1 & line_3:
            {
                'amount': 240.0,
                'debit_amount_currency': 480.0,
                'credit_amount_currency': 1440.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_3.id,
            },
            # Partial generated when reconciling line_1 & line_4:
            {
                'amount': 720.0,
                'debit_amount_currency': 1440.0,
                'credit_amount_currency': 4320.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_4.id,
            },
        ])

        self.assertRecordValues(line_1 + line_3 + line_4, [
            {'amount_residual': 240.0,      'amount_residual_currency': 1680.0,     'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 480.0,      'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 1440.0,     'reconciled': False},
        ])

        res = (line_1 + line_5).reconcile()

        self.assertPartialReconcile(res['partials'], [{
            'amount': 240.0,
            'debit_amount_currency': 480.0,
            'credit_amount_currency': 1440.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_5.id,
        }])

        self.assertRecordValues(line_1 + line_5, [
            {'amount_residual': 0.0,        'amount_residual_currency': 1200.0,     'reconciled': False},
            {'amount_residual': -780.0,     'amount_residual_currency': -2640.0,    'reconciled': False},
        ])

        res = (line_2 + line_5).reconcile()

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids.sorted(lambda line: (line.currency_id, abs(line.amount_currency), -line.amount_currency))

        self.assertRecordValues(exchange_diff_lines, [
            # Fix line_2:
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 780.0,
                'currency_id': currency1_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -780.0,
                'currency_id': currency1_id,
                'account_id': account_id,
            },
            # Fix line_3:
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 480.0,
                'currency_id': currency2_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -480.0,
                'currency_id': currency2_id,
                'account_id': account_id,
            },
            # Fix line_4:
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 1440.0,
                'currency_id': currency2_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -1440.0,
                'currency_id': currency2_id,
                'account_id': account_id,
            },
            # Fix line_5:
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 2040.0,
                'currency_id': currency2_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -2040.0,
                'currency_id': currency2_id,
                'account_id': account_id,
            },
            # Fix line_1:
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 1200.0,
                'currency_id': currency1_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -1200.0,
                'currency_id': currency1_id,
                'account_id': account_id,
            },
        ])

        self.assertPartialReconcile(res['partials'], [
            # Partial fixing line_3 (exchange difference):
            {
                'amount': 0.0,
                'debit_amount_currency': 480.0,
                'credit_amount_currency': 480.0,
                'debit_move_id': line_3.id,
                'credit_move_id': exchange_diff_lines[3].id,
            },
            # Partial fixing line_2 (exchange difference):
            {
                'amount': 0.0,
                'debit_amount_currency': 780.0,
                'credit_amount_currency': 780.0,
                'debit_move_id': line_2.id,
                'credit_move_id': exchange_diff_lines[1].id,
            },
            # Partial fixing line_1 (exchange difference):
            {
                'amount': 0.0,
                'debit_amount_currency': 1200.0,
                'credit_amount_currency': 1200.0,
                'debit_move_id': line_1.id,
                'credit_move_id': exchange_diff_lines[9].id,
            },
            # Partial fixing line_4 (exchange difference):
            {
                'amount': 0.0,
                'debit_amount_currency': 1440.0,
                'credit_amount_currency': 1440.0,
                'debit_move_id': line_4.id,
                'credit_move_id': exchange_diff_lines[5].id,
            },
            # Partial fixing line_5 (exchange difference):
            {
                'amount': 0.0,
                'debit_amount_currency': 2040.0,
                'credit_amount_currency': 2040.0,
                'debit_move_id': line_5.id,
                'credit_move_id': exchange_diff_lines[7].id,
            },
            # Partial generated when reconciling line_2 & line_5:
            {
                'amount': 780.0,
                'debit_amount_currency': 1560.0,
                'credit_amount_currency': 4680.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_5.id,
            },
        ])

        self.assertFullReconcile(res['full_reconcile'], line_1 + line_2 + line_3 + line_4 + line_5)

    def test_reconcile_asymetric_rate_change(self):
        account_id = self.company_data['default_account_receivable'].id

        # Rate is 3.0 in 2016, 2.0 in 2017.
        currency1_id = self.currency_data['currency'].id
        # Rate is 6.0 in 2016, 4.0 in 2017.
        currency2_id = self.currency_data_2['currency'].id

        # Create rate changes for 2018: currency1 rate increases while currency2 rate decreases.
        self.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 8.0,
            'currency_id': currency1_id,
            'company_id': self.company_data['company'].id,
        })

        self.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 2.0,
            'currency_id': currency2_id,
            'company_id': self.company_data['company'].id,
        })

        moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2018-01-01',
                'line_ids': [
                    (0, 0, {
                        'debit': 1200.0,
                        'credit': 0.0,
                        'amount_currency': 9600.0,
                        'account_id': account_id,
                        'currency_id': currency1_id,
                    }),
                    (0, 0, {
                        'debit': 960.0,
                        'credit': 0.0,
                        'amount_currency': 1920.0,
                        'account_id': account_id,
                        'currency_id': currency2_id,
                    }),
                    (0, 0, {
                        'debit': 0.0,
                        'credit': 2160.0,
                        'account_id': account_id,
                    }),
                ]
            },
            {
                'move_type': 'entry',
                'date': '2017-01-01',
                'line_ids': [
                    (0, 0, {
                        'debit': 0.0,
                        'credit': 1200.0,
                        'amount_currency': -4800.0,
                        'account_id': account_id,
                        'currency_id': currency2_id,
                    }),
                    (0, 0, {
                        'debit': 0.0,
                        'credit': 960.0,
                        'amount_currency': -1920.0,
                        'account_id': account_id,
                        'currency_id': currency1_id,
                    }),
                    (0, 0, {
                        'debit': 2160.0,
                        'credit': 0.0,
                        'account_id': account_id,
                    }),
                ]
            }
        ])

        moves.action_post()

        line_1 = moves.line_ids.filtered(lambda line: line.debit == 1200.0)
        line_2 = moves.line_ids.filtered(lambda line: line.debit == 960.0)
        line_3 = moves.line_ids.filtered(lambda line: line.credit == 1200.0)
        line_4 = moves.line_ids.filtered(lambda line: line.credit == 960.0)

        self.assertRecordValues(line_1 + line_2 + line_3 + line_4, [
            {'amount_residual': 1200.0,     'amount_residual_currency': 9600.0,     'reconciled': False},
            {'amount_residual': 960.0,      'amount_residual_currency': 1920.0,     'reconciled': False},
            {'amount_residual': -1200.0,    'amount_residual_currency': -4800.0,    'reconciled': False},
            {'amount_residual': -960.0,     'amount_residual_currency': -1920.0,    'reconciled': False},
        ])

        # Reconcile with debit_line currency rate increased and credit_line currency rate decreased between
        # credit_line.date and debit_line.date.

        res = (line_1 + line_3).reconcile()

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids.sorted(lambda line: (line.currency_id, abs(line.amount_currency), -line.amount_currency))

        self.assertRecordValues(exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 2400.0,
                'currency_id': currency2_id,
                'account_id': account_id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -2400.0,
                'currency_id': currency2_id,
                'account_id': exchange_diff.journal_id.company_id.income_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 7200.0,
                'currency_id': currency1_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -7200.0,
                'currency_id': currency1_id,
                'account_id': account_id,
            }
        ])

        self.assertPartialReconcile(res['partials'], [
            {
                'amount': 0.0,
                'debit_amount_currency': 2400.0,
                'credit_amount_currency': 2400.0,
                'debit_move_id': exchange_diff_lines[0].id,
                'credit_move_id': line_3.id,
            },
            {
                'amount': 0.0,
                'debit_amount_currency': 7200.0,
                'credit_amount_currency': 7200.0,
                'debit_move_id': line_1.id,
                'credit_move_id': exchange_diff_lines[3].id,
            },
            {
                'amount': 1200.0,
                'debit_amount_currency': 2400.0,
                'credit_amount_currency': 2400.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_3.id,
            },
        ])

        self.assertRecordValues(line_1 + line_3, [
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True},
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True},
        ])

        # Reconcile with debit_line currency rate decreased and credit_line currency rate increased between
        # credit_line.date and debit_line.date.

        res = (line_2 + line_4).reconcile()

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids.sorted(lambda line: (line.currency_id, abs(line.amount_currency), -line.amount_currency))

        self.assertRecordValues(exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 5760.0,
                'currency_id': currency1_id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -5760.0,
                'currency_id': currency1_id,
                'account_id': account_id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 1920.0,
                'currency_id': currency2_id,
                'account_id': account_id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -1920.0,
                'currency_id': currency2_id,
                'account_id': exchange_diff.journal_id.company_id.income_currency_exchange_account_id.id,
            }
        ])

        self.assertPartialReconcile(res['partials'], [
            {
                'amount': 0.0,
                'debit_amount_currency': 1920.0,
                'credit_amount_currency': 1920.0,
                'debit_move_id': exchange_diff_lines[2].id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 0.0,
                'debit_amount_currency': 5760.0,
                'credit_amount_currency': 5760.0,
                'debit_move_id': line_4.id,
                'credit_move_id': exchange_diff_lines[1].id,
            },
            {
                'amount': 960.0,
                'debit_amount_currency': 3840.0,
                'credit_amount_currency': 7680.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_4.id,
            },
        ])

        self.assertRecordValues(line_2 + line_4, [
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True},
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True},
        ])

    def test_reverse_with_multiple_lines(self):
        """
        Test if all lines from a reversed entry are fully reconciled
        """
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'debit': 1200.0,
                    'credit': 0.0,
                    'amount_currency': 3600.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 200.0,
                    'account_id': self.company_data['default_account_payable'].id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 400.0,
                    'account_id': self.company_data['default_account_payable'].id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 600.0,
                    'account_id': self.company_data['default_account_payable'].id,
                }),
            ],
        })

        move.action_post()

        lines_to_reconcile = move.line_ids.filtered(lambda x: (x.account_id.reconcile or x.account_id.internal_type == 'liquidity') and not x.reconciled)

        self.assertRecordValues(lines_to_reconcile, [
            {'debit': 1200.0, 'credit': 0.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 200.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 400.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 600.0, 'reconciled': False},
        ])

        reversed_move = move._reverse_moves(cancel=True)

        reversed_lines = reversed_move.line_ids.filtered(lambda x: (
                x.account_id.reconcile or x.account_id.internal_type == 'liquidity'
        ))

        self.assertRecordValues(reversed_lines, [
            {'debit': 0.0, 'credit': 1200.0, 'reconciled': True},
            {'debit': 200.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 400.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 600.0, 'credit': 0.0, 'reconciled': True},
        ])

        self.assertTrue(all([line.full_reconcile_id for line in reversed_lines]))

    def test_reverse_exchange_difference_same_foreign_currency(self):
        move_2016 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 1200.0,
                    'credit': 0.0,
                    'amount_currency': 3600.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                    'currency_id': self.currency_data['currency'].id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1200.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        move_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1800.0,
                    'amount_currency': -3600.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                    'currency_id': self.currency_data['currency'].id,
                }),
                (0, 0, {
                    'debit': 1800.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        (move_2016 + move_2017).action_post()

        rec_line_2016 = move_2016.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable')
        rec_line_2017 = move_2017.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable')

        self.assertRecordValues(rec_line_2016 + rec_line_2017, [
            {'amount_residual': 1200.0,     'amount_residual_currency': 3600.0,     'reconciled': False},
            {'amount_residual': -1800.0,    'amount_residual_currency': -3600.0,    'reconciled': False},
        ])

        # Reconcile.

        res = (rec_line_2016 + rec_line_2017).reconcile()

        self.assertRecordValues(rec_line_2016 + rec_line_2017, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids.sorted('balance')

        self.assertRecordValues(exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 600.0,
                'amount_currency': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': exchange_diff.journal_id.company_id.income_currency_exchange_account_id.id,
            },
            {
                'debit': 600.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
        ])

        self.assertRecordValues(exchange_diff_lines, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        # Unreconcile.
        # A reversal is created to cancel the exchange difference journal entry.

        (rec_line_2016 + rec_line_2017).remove_move_reconcile()

        reverse_exchange_diff = exchange_diff_lines[1].matched_credit_ids.credit_move_id.move_id
        reverse_exchange_diff_lines = reverse_exchange_diff.line_ids.sorted('balance')

        self.assertRecordValues(reverse_exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 600.0,
                'amount_currency': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 600.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': exchange_diff.journal_id.company_id.income_currency_exchange_account_id.id,
            },
        ])

        self.assertRecordValues(exchange_diff_lines + reverse_exchange_diff_lines, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
        ])

        partials = reverse_exchange_diff_lines.matched_debit_ids + reverse_exchange_diff_lines.matched_credit_ids
        self.assertPartialReconcile(partials, [{
            'amount': 600.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': exchange_diff_lines[1].id,
            'credit_move_id': reverse_exchange_diff_lines[0].id,
        }])

    def test_reverse_exchange_multiple_foreign_currencies(self):
        move_2016 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 1200.0,
                    'credit': 0.0,
                    'amount_currency': 7200.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                    'currency_id': self.currency_data_2['currency'].id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1200.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        move_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1200.0,
                    'amount_currency': -2400.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                    'currency_id': self.currency_data['currency'].id,
                }),
                (0, 0, {
                    'debit': 1200.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        (move_2016 + move_2017).action_post()

        rec_line_2016 = move_2016.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable')
        rec_line_2017 = move_2017.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable')

        self.assertRecordValues(rec_line_2016 + rec_line_2017, [
            {'amount_residual': 1200.0,     'amount_residual_currency': 7200.0,     'reconciled': False},
            {'amount_residual': -1200.0,    'amount_residual_currency': -2400.0,    'reconciled': False},
        ])

        # Reconcile.

        res = (rec_line_2016 + rec_line_2017).reconcile()

        self.assertRecordValues(rec_line_2016 + rec_line_2017, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids.sorted('amount_currency')

        self.assertRecordValues(exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -2400.0,
                'currency_id': self.currency_data_2['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -1200.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 1200.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 2400.0,
                'currency_id': self.currency_data_2['currency'].id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
        ])

        self.assertRecordValues(exchange_diff_lines, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
        ])

        # Unreconcile.
        # A reversal is created to cancel the exchange difference journal entry.

        (rec_line_2016 + rec_line_2017).remove_move_reconcile()

        reverse_exchange_diff = exchange_diff_lines[1].matched_debit_ids.debit_move_id.move_id
        reverse_exchange_diff_lines = reverse_exchange_diff.line_ids.sorted('amount_currency')

        self.assertRecordValues(reverse_exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -2400.0,
                'currency_id': self.currency_data_2['currency'].id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -1200.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': exchange_diff.journal_id.company_id.expense_currency_exchange_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 1200.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 2400.0,
                'currency_id': self.currency_data_2['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
        ])

        self.assertRecordValues(exchange_diff_lines + reverse_exchange_diff_lines, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        partials = reverse_exchange_diff_lines.matched_debit_ids + reverse_exchange_diff_lines.matched_credit_ids
        self.assertPartialReconcile(partials, [
            {
                'amount': 0.0,
                'debit_amount_currency': 1200.0,
                'credit_amount_currency': 1200.0,
                'debit_move_id': reverse_exchange_diff_lines[2].id,
                'credit_move_id': exchange_diff_lines[1].id,
            },
            {
                'amount': 0.0,
                'debit_amount_currency': 2400.0,
                'credit_amount_currency': 2400.0,
                'debit_move_id': reverse_exchange_diff_lines[3].id,
                'credit_move_id': exchange_diff_lines[0].id,
            },
        ])

    def test_reconcile_rounding_issue(self):
        rate = 1/1.5289
        currency = self.setup_multi_currency_data(default_values={
            'name': 'XXX',
            'symbol': 'XXX',
            'currency_unit_label': 'XX',
            'currency_subunit_label': 'X',
            'rounding': 0.01,
        }, rate2016=rate, rate2017=rate)['currency']

        # Create an invoice 26.45 XXX = 40.43 USD
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 23.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
            })],
        })
        invoice.action_post()

        # Pay it with 100.0 USD
        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'amount': 100.0, 'currency_id': self.company_data['currency'].id})\
            ._create_payments()

        self.assertTrue(invoice.payment_state in ('in_payment', 'paid'))

    # -------------------------------------------------------------------------
    # Test creation of extra journal entries during the reconciliation to
    # deal with taxes that are exigible on payment (cash basis).
    # -------------------------------------------------------------------------

    def test_reconcile_cash_basis_workflow_single_currency(self):
        ''' Test the generated journal entries during the reconciliation to manage the cash basis taxes.
        Also,
        - Test the case when there is multiple receivable/payable accounts.
        - Test the reconciliation with tiny amounts.
        - Check there is no rounding issue when making the percentage.
        - Check there is no lost cents when the journal entry is fully reconciled.
        '''
        self.env.company.tax_exigibility = True
        cash_basis_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, (self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount).ids)],
                }),

                # Tax lines
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.33,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 0.01,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_tiny_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 44.45,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_1.id,
                }),
                (0, 0, {
                    'debit': 44.45,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_2.id,
                }),
                (0, 0, {
                    'debit': 44.45,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_2.id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 0.01,
                    'account_id': self.extra_payable_account_1.id,
                }),
            ]
        })

        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 33.34,    'account_id': self.extra_receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 11.11,    'account_id': self.extra_receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 88.89,    'account_id': self.extra_receivable_account_2.id}),
                (0, 0, {'debit': 0.0,       'credit': 0.01,     'account_id': self.extra_receivable_account_2.id}),
                (0, 0, {'debit': 0.01,      'credit': 0.0,      'account_id': self.extra_payable_account_1.id}),
                (0, 0, {'debit': 133.34,    'credit': 0.0,      'account_id': self.company_data['default_account_revenue'].id}),
            ]
        })

        (cash_basis_move + payment_move).action_post()

        # Initial amounts by accounts:

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -33.34,     -33.34),
            (self.tax_account_1,                    0.0,        0.0),
            (self.tax_account_2,                    0.0,        0.0),
            (self.cash_basis_base_account,          0.0,        0.0),
        ])

        # There is 44.45 + 44.45 + 44.45 + 0.01 = 133.36 to reconcile on 'cash_basis_move'.
        # Reconciling all the amount in extra_receivable_account_1 should compute 2 percentages:
        # 33.34 / 133.36 = 0.25
        # 11.11 / 133.36 = 0.083308338

        receivable_lines_1 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines_1.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines_1)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 2)
        self.assertRecordValues(res['tax_cash_basis_moves'][0].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 25.0,     'credit': 0.0,      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 25.0,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 8.33,     'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 8.33,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_2.id},
        ])
        self.assertRecordValues(res['tax_cash_basis_moves'][1].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 8.33,     'credit': 0.0,      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 8.33,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 2.78,     'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 2.78,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_2.id},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -22.23,     -22.23),
            (self.tax_account_1,                    -11.11,     -11.11),
            (self.tax_account_2,                    0.0,        0.0),
        ])

        # Reconciling all the amount in extra_receivable_account_2 should compute 3 percentages:
        # 44.45 / 133.36 = 0.333308338
        # 44.44 / 133.36 = 0.333233353
        # 0.01 / 133.36 = 0.000074985

        receivable_lines_2 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_2)
        res = receivable_lines_2.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines_2)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 3)
        self.assertRecordValues(res['tax_cash_basis_moves'][0].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 33.33,    'credit': 0.0,      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 33.33,    'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 11.11,    'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 11.11,    'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_2.id},
        ])
        self.assertRecordValues(res['tax_cash_basis_moves'][1].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 33.32,    'credit': 0.0,      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 33.32,    'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 11.11,    'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 11.11,    'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_2.id},
        ])
        self.assertRecordValues(res['tax_cash_basis_moves'][2].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 0.01,     'credit': 0.0,      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 0.01,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_2.id},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -0.01,      -0.01),
            (self.tax_account_1,                    -33.33,     -33.33),
            (self.tax_account_2,                    0.0,        0.0),
        ])

        # Reconciling all the amount in extra_payable_account_1 should trigger the matching number and ensure all
        # the base amount has been covered without any rounding issue.

        payable_lines_1 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_payable_account_1)
        res = payable_lines_1.reconcile()

        self.assertFullReconcile(res['full_reconcile'], payable_lines_1)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 1)
        self.assertRecordValues(res['tax_cash_basis_moves'].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 0.01,     'credit': 0.0,      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 0.01,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'account_id': self.tax_account_2.id},
        ])

        self.assertRecordValues(res['full_reconcile'].exchange_move_id.line_ids, [
            {'account_id': self.tax_account_2.id,               'debit': 0.0,   'credit': 0.01, 'tax_ids': [],          'tax_line_id': self.cash_basis_tax_tiny_amount.id},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 0.01,  'credit': 0.0,  'tax_ids': [],          'tax_line_id': False},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -33.33,     -33.33),
            (self.tax_account_2,                    -0.01,      -0.01),
        ])

    def test_reconcile_cash_basis_workflow_multi_currency(self):
        ''' Same as before with a foreign currency. '''

        self.env.company.tax_exigibility = True
        currency_id = self.currency_data['currency'].id
        taxes = self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount

        cash_basis_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.34,
                    'amount_currency': -100.0,
                    'currency_id': currency_id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, taxes.ids)],
                }),

                # Tax lines
                (0, 0, {
                    'debit': 0.0,
                    'credit': 11.10,
                    'amount_currency': -33.33,
                    'currency_id': currency_id,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 0.01,
                    'amount_currency': -0.01,
                    'currency_id': currency_id,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_tiny_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 14.82,
                    'credit': 0.0,
                    'amount_currency': 44.45,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
                (0, 0, {
                    'debit': 14.82,
                    'credit': 0.0,
                    'amount_currency': 44.45,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_2.id,
                }),
                (0, 0, {
                    'debit': 14.82,
                    'credit': 0.0,
                    'amount_currency': 44.45,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_2.id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 0.01,
                    'amount_currency': -0.01,
                    'currency_id': currency_id,
                    'account_id': self.extra_payable_account_1.id,
                }),
            ]
        })

        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 16.67,    'amount_currency': -33.34,  'currency_id': currency_id,     'account_id': self.extra_receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 5.6,      'amount_currency': -11.11,  'currency_id': currency_id,     'account_id': self.extra_receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 44.45,    'amount_currency': -88.89,  'currency_id': currency_id,     'account_id': self.extra_receivable_account_2.id}),
                (0, 0, {'debit': 0.0,       'credit': 0.01,     'amount_currency': -0.01,   'currency_id': currency_id,     'account_id': self.extra_receivable_account_2.id}),
                (0, 0, {'debit': 0.01,      'credit': 0.0,      'amount_currency': 0.01,    'currency_id': currency_id,     'account_id': self.extra_payable_account_1.id}),
                (0, 0, {'debit': 66.72,     'credit': 0.0,                                                                  'account_id': self.company_data['default_account_revenue'].id}),
            ]
        })

        (cash_basis_move + payment_move).action_post()

        # Initial amounts by accounts:

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -11.11,     -33.34),
            (self.tax_account_1,                    0.0,        0.0),
            (self.tax_account_2,                    0.0,        0.0),
        ])

        # There is 44.45 + 44.45 + 44.45 + 0.01 = 133.36 to reconcile on 'cash_basis_move'.
        # Reconciling all the amount in extra_receivable_account_1 should compute 2 percentages:
        # 33.34 / 133.36 = 0.25
        # 11.11 / 133.36 = 0.083308338

        receivable_lines_1 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines_1.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines_1)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 2)
        self.assertRecordValues(res['tax_cash_basis_moves'][0].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 12.5,     'credit': 0.0,      'amount_currency': 25.0,    'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 12.5,     'amount_currency': -25.0,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 4.17,     'credit': 0.0,      'amount_currency': 8.333,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 4.17,     'amount_currency': -8.333,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.003,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -0.003,  'currency_id': currency_id,     'account_id': self.tax_account_2.id},
        ])
        self.assertRecordValues(res['tax_cash_basis_moves'][1].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 4.2,      'credit': 0.0,      'amount_currency': 8.331,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 4.2,      'amount_currency': -8.331,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 1.4,      'credit': 0.0,      'amount_currency': 2.777,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 1.4,      'amount_currency': -2.777,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.001,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -0.001,  'currency_id': currency_id,     'account_id': self.tax_account_2.id},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -5.54,      -22.226),
            (self.tax_account_1,                    -5.57,      -11.11),
            (self.tax_account_2,                    0.0,        -0.004),
        ])

        # Reconciling all the amount in extra_receivable_account_2 should compute 3 percentages:
        # 44.45 / 133.36 = 0.333308338
        # 44.44 / 133.36 = 0.333233353
        # 0.01 / 133.36 = 0.000074985

        receivable_lines_2 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_2)
        res = receivable_lines_2.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines_2)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 3)
        self.assertRecordValues(res['tax_cash_basis_moves'][0].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 16.67,    'credit': 0.0,      'amount_currency': 33.331,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 16.67,    'amount_currency': -33.331, 'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 5.56,     'credit': 0.0,      'amount_currency': 11.109,  'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 5.56,     'amount_currency': -11.109, 'currency_id': currency_id,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.003,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -0.003,  'currency_id': currency_id,     'account_id': self.tax_account_2.id},
        ])
        self.assertRecordValues(res['tax_cash_basis_moves'][1].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 16.66,    'credit': 0.0,      'amount_currency': 33.323,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 16.66,    'amount_currency': -33.323, 'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 5.55,     'credit': 0.0,      'amount_currency': 11.107,  'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 5.55,     'amount_currency': -11.107, 'currency_id': currency_id,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.003,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -0.003,  'currency_id': currency_id,     'account_id': self.tax_account_2.id},
        ])
        self.assertRecordValues(res['tax_cash_basis_moves'][2].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 0.01,     'credit': 0.0,      'amount_currency': 0.007,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 0.01,     'amount_currency': -0.007,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.002,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -0.002,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.tax_account_2.id},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      5.57,       -0.002),
            (self.tax_account_1,                    -16.68,     -33.328),
            (self.tax_account_2,                    0.0,        -0.01),
        ])

        # Reconciling all the amount in extra_payable_account_1 should trigger the matching number and ensure all
        # the base amount has been covered without any rounding issue.

        payable_lines_1 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_payable_account_1)
        res = payable_lines_1.reconcile()

        self.assertFullReconcile(res['full_reconcile'], payable_lines_1)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 1)
        self.assertRecordValues(res['tax_cash_basis_moves'].line_ids, [
            # Base amount of tax_1 & tax_2:
            {'debit': 0.01,     'credit': 0.0,      'amount_currency': 0.007,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 0.01,     'amount_currency': -0.007,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.002,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': -0.002,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.tax_account_2.id},
        ])

        self.assertRecordValues(res['full_reconcile'].exchange_move_id.line_ids, [
            {'account_id': self.cash_basis_base_account.id,     'debit': 16.71, 'credit': 0.0,      'tax_ids': taxes.ids,   'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,   'credit': 16.71,    'tax_ids': [],          'tax_line_id': False},
            {'account_id': self.tax_account_1.id,               'debit': 5.58,  'credit': 0.0,      'tax_ids': [],          'tax_line_id': self.cash_basis_tax_a_third_amount.id},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 0.0,   'credit': 5.58,     'tax_ids': [],          'tax_line_id': False},
            {'account_id': self.tax_account_2.id,               'debit': 0.0,   'credit': 0.01,     'tax_ids': [],          'tax_line_id': self.cash_basis_tax_tiny_amount.id},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 0.01,  'credit': 0.0,      'tax_ids': [],          'tax_line_id': False},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -11.1,      -33.33),
            (self.tax_account_2,                    -0.01,      -0.01),
        ])

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_1(self):
        ''' Test the generation of the exchange difference for a tax cash basis journal entry when the transfer
        account is not reconcilable.
        '''
        self.env.company.tax_exigibility = True
        currency_id = self.currency_data['currency'].id

        # Rate 1/3 in 2016.
        cash_basis_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -300.0,
                    'currency_id': currency_id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.33,
                    'amount_currency': -100.0,
                    'currency_id': currency_id,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 133.33,
                    'credit': 0.0,
                    'amount_currency': 400.0,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        # Rate 1/2 in 2017.
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 0.0,
                    'credit': 201.0,
                    'amount_currency': -402.0, # Don't create the full reconcile directly.
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
                (0, 0, {
                    'debit': 201.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ]
        })

        # Move making the payment fully paid.
        end_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 1.0,
                    'credit': 0.0,
                    'amount_currency': 2.0,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ]
        })

        (cash_basis_move + payment_move + end_move).action_post()

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -33.33,     -100.0),
            (self.tax_account_1,                    0.0,        0.0),
        ])

        receivable_lines = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines.reconcile()

        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 1)
        self.assertRecordValues(res['tax_cash_basis_moves'].line_ids, [
            # Base amount:
            {'debit': 150.0,    'credit': 0.0,      'amount_currency': 300.0,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 150.0,    'amount_currency': -300.0,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax:
            {'debit': 50.0,     'credit': 0.0,      'amount_currency': 100.0,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 50.0,     'amount_currency': -100.0,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
        ])

        receivable_lines2 = (payment_move + end_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines2.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines + receivable_lines2)

        exchange_diff = res['full_reconcile'].exchange_move_id
        exchange_diff_lines = exchange_diff.line_ids\
            .filtered(lambda line: line.account_id == self.cash_basis_transfer_account)\
            .sorted(lambda line: (line.account_id, line.debit, line.credit))

        self.assertRecordValues(exchange_diff_lines, [
            {
                'debit': 0.0,
                'credit': 16.67,
                'amount_currency': 0.0,
                'currency_id': currency_id,
                'account_id': self.cash_basis_transfer_account.id,
            },
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -33.33,     -100.0),
        ])

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_2(self):
        ''' Test the generation of the exchange difference for a tax cash basis journal entry when the transfer
        account is not a reconcile one.
        '''
        self.env.company.tax_exigibility = True
        currency_id = self.setup_multi_currency_data(default_values={
            'name': 'bitcoin',
            'symbol': 'bc',
            'currency_unit_label': 'Bitcoin',
            'currency_subunit_label': 'Tiny bitcoin',
        }, rate2016=0.5, rate2017=0.66666666666666)['currency'].id

        # Rate 2/1 in 2016.
        caba_inv = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 200.0,
                    'amount_currency': -100.0,
                    'currency_id': currency_id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 20.0,
                    'amount_currency': -10.0,
                    'currency_id': currency_id,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 220.0,
                    'credit': 0.0,
                    'amount_currency': 110.0,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })
        caba_inv.action_post()

        # Rate 3/2 in 2017. Full payment of 110 in foreign currency
        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=caba_inv.ids).create({
            'payment_date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        pmt_wizard._create_payments()
        partial_rec = caba_inv.mapped('line_ids.matched_credit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', partial_rec.ids)])

        self.assertRecordValues(caba_move.line_ids, [
            {'account_id': self.cash_basis_base_account.id,     'debit': 150.0, 'credit': 0.0,      'amount_currency': 100.0,   'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,   'credit': 150.0,    'amount_currency': -100.0,  'tax_ids': self.cash_basis_tax_a_third_amount.ids,  'tax_line_id': False},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 15.0,  'credit': 0.0,      'amount_currency': 10.0,    'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.tax_account_1.id,               'debit': 0.0,   'credit': 15.0,     'amount_currency': -10.0,   'tax_ids': [],                                      'tax_line_id': self.cash_basis_tax_a_third_amount.id},
        ])

        receivable_line = caba_inv.line_ids.filtered(lambda x: x.account_id.internal_type == 'receivable')
        self.assertTrue(receivable_line.full_reconcile_id, "Invoice should be fully paid")

        exchange_move = receivable_line.full_reconcile_id.exchange_move_id
        self.assertTrue(exchange_move, "There should be an exchange difference move created")
        self.assertRecordValues(exchange_move.line_ids, [
            {'account_id': receivable_line.account_id.id,                                   'debit': 0.0,   'credit': 55.0, 'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': caba_move.company_id.expense_currency_exchange_account_id.id,    'debit': 55.0,  'credit': 0.0,  'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,                                 'debit': 0.0,   'credit': 50.0, 'amount_currency': 0.0, 'tax_ids': self.cash_basis_tax_a_third_amount.ids,  'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,                                 'debit': 50.0,  'credit': 0.0,  'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.tax_account_1.id,                                           'debit': 0.0,   'credit': 5.0,  'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': self.cash_basis_tax_a_third_amount.id},
            {'account_id': self.cash_basis_transfer_account.id,                             'debit': 5.0,   'credit': 0.0,  'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': False},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -20.0,      -10.0),
        ])

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_3(self):
        ''' Test the generation of the exchange difference for a tax cash basis journal entry when the transfer
        account is not a reconcile one.
        '''
        self.env.company.tax_exigibility = True
        currency_id = self.setup_multi_currency_data(default_values={
            'name': 'bitcoin',
            'symbol': 'bc',
            'currency_unit_label': 'Bitcoin',
            'currency_subunit_label': 'Tiny bitcoin',
            'rounding': 0.01,
        }, rate2016=0.5, rate2017=0.66666666666666)['currency'].id

        # Rate 2/1 in 2016.
        caba_inv = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 200.0,
                    'amount_currency': -100.0,
                    'currency_id': currency_id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 20.0,
                    'amount_currency': -10.0,
                    'currency_id': currency_id,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 220.0,
                    'credit': 0.0,
                    'amount_currency': 110.0,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })
        caba_inv.action_post()

        # Rate 3/2 in 2017. Full payment of 220 in company currency
        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=caba_inv.ids).create({
            'payment_date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
            'currency_id': self.company_data['currency'].id,
            'amount': 220.0,
        })
        pmt_wizard._create_payments()

        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', caba_inv.line_ids.matched_credit_ids.ids)])
        self.assertRecordValues(caba_move.line_ids, [
            {'account_id': self.cash_basis_base_account.id,     'debit': 200.01,    'credit': 0.0,      'amount_currency': 133.34,  'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,       'credit': 200.01,   'amount_currency': -133.34, 'tax_ids': self.cash_basis_tax_a_third_amount.ids,  'tax_line_id': False},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 20.0,      'credit': 0.0,      'amount_currency': 13.33,   'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.tax_account_1.id,               'debit': 0.0,       'credit': 20.0,     'amount_currency': -13.33,  'tax_ids': [],                                      'tax_line_id': self.cash_basis_tax_a_third_amount.id},
        ])

        receivable_line = caba_inv.line_ids.filtered(lambda x: x.account_id.internal_type == 'receivable')
        self.assertTrue(receivable_line.full_reconcile_id, "Invoice should be fully paid")

        exchange_move = receivable_line.full_reconcile_id.exchange_move_id
        self.assertRecordValues(exchange_move.line_ids, [
            {'account_id': self.extra_receivable_account_1.id,                          'debit': 0.0,   'credit': 0.0,  'amount_currency': 36.67,   'tax_ids': [], 'tax_line_id': False},
            {'account_id': caba_move.company_id.income_currency_exchange_account_id.id, 'debit': 0.0,   'credit': 0.0,  'amount_currency': -36.67,  'tax_ids': [], 'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,                             'debit': 0.01,  'credit': 0.0,  'amount_currency': 0.0,     'tax_ids': self.cash_basis_tax_a_third_amount.ids,  'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,                             'debit': 0.0,   'credit': 0.01, 'amount_currency': 0.0,     'tax_ids': [],                                      'tax_line_id': False},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        3.33),
            (self.tax_account_1,                    -20.0,      -13.33),
        ])

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_4(self):
        ''' Test the generation of the exchange difference for a tax cash basis journal entry when the tax
        account is a reconcile one.
        '''
        self.env.company.tax_exigibility = True
        currency_id = self.currency_data['currency'].id
        cash_basis_transition_account = self.env['account.account'].create({
            'code': '209.01.01',
            'name': 'Cash Basis Transition Account',
            'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
            'company_id': self.company_data['company'].id,
            'reconcile': True,
        })
        self.cash_basis_tax_a_third_amount.write({
            'cash_basis_transition_account_id': cash_basis_transition_account.id,
        })

        # Rate 1/3 in 2016.
        cash_basis_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -300.0,
                    'currency_id': currency_id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.33,
                    'amount_currency': -100.0,
                    'currency_id': currency_id,
                    'account_id': cash_basis_transition_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 133.33,
                    'credit': 0.0,
                    'amount_currency': 400.0,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        # Rate 1/2 in 2017.
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {
                    'debit': 0.0,
                    'credit': 200.0,
                    'amount_currency': -400.0,
                    'currency_id': currency_id,
                    'account_id': self.extra_receivable_account_1.id,
                }),
                (0, 0, {
                    'debit': 200.0,
                    'credit': 0.0,
                    'amount_currency': 400.0,
                    'currency_id': currency_id,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ]
        })

        (cash_basis_move + payment_move).action_post()

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (cash_basis_transition_account,      -33.33,     -100.0),
            (self.tax_account_1,                    0.0,        0.0),
        ])

        receivable_lines = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines.reconcile()

        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 1)

        # Tax values based on payment
        # Invoice amount 300 (amount currency) with payment rate 2 (400 payment amount divided by 200 invoice balance)
        #  - Base amount: 150 company currency
        #  - Tax amount: 50 company currency
        self.assertRecordValues(res['tax_cash_basis_moves'].line_ids, [
            # Base amount:
            {'debit': 150.0,    'credit': 0.0,      'amount_currency': 300.0,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 150.0,    'amount_currency': -300.0,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax:
            {'debit': 50.0,     'credit': 0.0,      'amount_currency': 100.0,   'currency_id': currency_id,     'account_id': cash_basis_transition_account.id},
            {'debit': 0.0,      'credit': 50.0,     'amount_currency': -100.0,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
        ])

        exchange_diff = res['full_reconcile'].exchange_move_id

        # Exchange difference
        # 66.67 amount residual on the payment line after reconciling receivable line of the cash basis move with the payment counterpart
        # 50.00 difference of the cash_basis_move base line and the CABA entry created by the system
        self.assertRecordValues(exchange_diff.line_ids, [
            {'debit': 66.67,    'credit': 0.0,      'currency_id': currency_id,     'account_id': self.extra_receivable_account_1.id},
            {'debit': 0.0,      'credit': 66.67,    'currency_id': currency_id,     'account_id': self.company_data['company'].income_currency_exchange_account_id.id},
            {'debit': 50.0,     'credit': 0.0,      'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 50.0,     'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
        ])

    def test_reconcile_cash_basis_refund_multicurrency(self):
        self.env.company.tax_exigibility = True
        rates_data = self.setup_multi_currency_data(default_values={
            'name': 'Playmock',
            'symbol': '🦌',
            'rounding': 0.01,
            'currency_unit_label': 'Playmock',
            'currency_subunit_label': 'Cent',
        }, rate2016=0.5, rate2017=0.33333333333333333)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': rates_data['currency'].id,
            'invoice_date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'dudu',
                'account_id': self.company_data['default_account_revenue'].id,
                'price_unit': 100.0,
                'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
            })],
        })

        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'currency_id': rates_data['currency'].id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'dudu',
                'account_id': self.company_data['default_account_revenue'].id,
                'price_unit': 100.0,
                'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
            })],
        })

        invoice.action_post()
        refund.action_post()

        (refund + invoice).line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'receivable').reconcile()

        # Check the cash basis moves
        self.assertRecordValues(
            self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)]).line_ids,
            [
                {
                    'debit': 200,
                    'credit': 0,
                    'amount_currency': 100,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': [],
                },
                {
                    'debit': 0,
                    'credit': 200,
                    'amount_currency': -100,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': self.cash_basis_tax_a_third_amount.ids,
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': self.tax_tags[0].ids,
                },
                {
                    'debit': 66.66,
                    'credit': 0,
                    'amount_currency': 33.33,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': [],
                },
                {
                    'debit': 0,
                    'credit': 66.66,
                    'amount_currency': -33.33,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_tag_ids': self.tax_tags[1].ids,
                },
            ]
        )

        self.assertRecordValues(
            self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', refund.id)]).line_ids,
            [
                {
                    'debit': 0,
                    'credit': 300,
                    'amount_currency': -100,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': [],
                },
                {
                    'debit': 300,
                    'credit': 0,
                    'amount_currency': 100,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': self.cash_basis_tax_a_third_amount.ids,
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': self.tax_tags[2].ids,
                },
                {
                    'debit': 0,
                    'credit': 99.99,
                    'amount_currency': -33.33,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': [],
                },
                {
                    'debit': 99.99,
                    'credit': 0,
                    'amount_currency': 33.33,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_tag_ids': self.tax_tags[3].ids,
                },
            ]
        )

        # Check the exchange difference move, to be sure no cash basis rounding data was added into it
        self.assertRecordValues(
            invoice.line_ids.full_reconcile_id.exchange_move_id.line_ids,
            [
                {
                    'debit': 133.33,
                    'credit': 0,
                    'amount_currency': 0,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': [],
                },
                {
                    'debit': 0,
                    'credit': 133.33,
                    'amount_currency': 0,
                    'currency_id': rates_data['currency'].id,
                    'tax_ids': [],
                    'tax_repartition_line_id': None,
                    'tax_tag_ids': [],
                },
            ]
        )

    def test_reconcile_cash_basis_revert(self):
        ''' Ensure the cash basis journal entry can be reverted. '''
        self.env.company.tax_exigibility = True
        self.cash_basis_transfer_account.reconcile = True
        self.cash_basis_tax_a_third_amount.cash_basis_transition_account_id = self.tax_account_1

        invoice_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.33,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable line
                (0, 0, {
                    'debit': 133.33,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 133.33,   'account_id': self.extra_receivable_account_1.id}),
                (0, 0, {'debit': 133.33,    'credit': 0.0,      'account_id': self.company_data['default_account_revenue'].id}),
            ]
        })

        (invoice_move + payment_move).action_post()

        receivable_lines = (invoice_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines.reconcile()

        # == Check reconciliation of invoice with payment ==

        self.assertFullReconcile(res['full_reconcile'], receivable_lines)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 1)

        # == Check the reconciliation of invoice with tax cash basis journal entry.
        # /!\ We make the assumption the tax cash basis journal entry is well created.

        tax_cash_basis_move = res['tax_cash_basis_moves']

        taxes_lines = (invoice_move.line_ids + tax_cash_basis_move.line_ids.filtered('debit'))\
            .filtered(lambda line: line.account_id == self.cash_basis_transfer_account)
        taxes_full_reconcile = taxes_lines.matched_debit_ids.full_reconcile_id

        self.assertTrue(taxes_full_reconcile)
        self.assertFullReconcile(taxes_full_reconcile, taxes_lines)

        # == Check the reconciliation after the reverse ==

        tax_cash_basis_move_reverse = tax_cash_basis_move._reverse_moves(cancel=True)

        self.assertFullReconcile(res['full_reconcile'], receivable_lines)

        # == Check the reconciliation of the tax cash basis journal entry with its reverse ==

        reversed_taxes_lines = (tax_cash_basis_move + tax_cash_basis_move_reverse).line_ids\
            .filtered(lambda line: line.account_id == self.cash_basis_transfer_account)

        reversed_taxes_full_reconcile = reversed_taxes_lines.matched_debit_ids.full_reconcile_id

        self.assertTrue(reversed_taxes_full_reconcile)
        self.assertFullReconcile(reversed_taxes_full_reconcile, reversed_taxes_lines)

    def test_reconcile_cash_basis_tax_grid_refund(self):
        self.env.company.tax_exigibility = True
        invoice_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.33,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable line
                (0, 0, {
                    'debit': 133.33,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        refund_move = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2016-01-01',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 100.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),

                # Tax line
                (0, 0, {
                    'debit': 33.33,
                    'credit': 0.0,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.refund_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 133.33,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        (invoice_move + refund_move).action_post()

        receivable_lines = (invoice_move + refund_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 2)

        tax_cash_basis_moves = res['tax_cash_basis_moves'].sorted(lambda move: move.tax_cash_basis_origin_move_id.id)

        # Invoice:
        cb_lines = tax_cash_basis_moves[0].line_ids.sorted(lambda line: (-abs(line.balance), -line.debit, line.account_id))
        self.assertRecordValues(cb_lines, [
            # Base amount:
            {'debit': 100.0,    'credit': 0.0,      'tax_tag_ids': [],                      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 100.0,    'tax_tag_ids': self.tax_tags[0].ids,    'account_id': self.cash_basis_base_account.id},
            # tax:
            {'debit': 33.33,    'credit': 0.0,      'tax_tag_ids': [],                      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 33.33,    'tax_tag_ids': self.tax_tags[1].ids,    'account_id': self.tax_account_1.id},
        ])

        # Refund:
        cb_lines = tax_cash_basis_moves[1].line_ids.sorted(lambda line: (-abs(line.balance), -line.debit, line.account_id))
        self.assertRecordValues(cb_lines, [
            # Base amount:
            {'debit': 100.0,    'credit': 0.0,      'tax_tag_ids': self.tax_tags[2].ids,    'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 100.0,    'tax_tag_ids': [],                      'account_id': self.cash_basis_base_account.id},
            # tax:
            {'debit': 33.33,    'credit': 0.0,      'tax_tag_ids': self.tax_tags[3].ids,    'account_id': self.tax_account_1.id},
            {'debit': 0.0,      'credit': 33.33,    'tax_tag_ids': [],                      'account_id': self.cash_basis_transfer_account.id},
        ])

    def test_reconcile_cash_basis_tax_grid_reversal(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
            })],
        })
        invoice.action_post()

        self.assertRecordValues(invoice.line_ids.sorted('balance'), [
            {'debit': 0.0,      'credit': 1000.0,   'tax_tag_ids': [],  'account_id': self.company_data['default_account_revenue'].id},
            {'debit': 0.0,      'credit': 333.33,   'tax_tag_ids': [],  'account_id': self.cash_basis_transfer_account.id},
            {'debit': 1333.33,  'credit': 0.0,      'tax_tag_ids': [],  'account_id': self.company_data['default_account_receivable'].id},
        ])

        reversal_wizard = self.env['account.move.reversal']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'reason': "test_reconcile_cash_basis_tax_grid_reversal",
                'refund_method': 'refund',
                'journal_id': invoice.journal_id.id,
            })
        refund = self.env['account.move'].browse(reversal_wizard.reverse_moves()['res_id'])
        refund.action_post()

        self.assertRecordValues(refund.line_ids.sorted('balance'), [
            {'debit': 0.0,      'credit': 1333.33,  'tax_tag_ids': [],  'account_id': self.company_data['default_account_receivable'].id},
            {'debit': 333.33,   'credit': 0.0,      'tax_tag_ids': [],  'account_id': self.cash_basis_transfer_account.id},
            {'debit': 1000.0,   'credit': 0.0,      'tax_tag_ids': [],  'account_id': self.company_data['default_account_revenue'].id},
        ])

        reversal_wizard = self.env['account.move.reversal']\
            .with_context(active_model='account.move', active_ids=refund.ids)\
            .create({
                'reason': "test_reconcile_cash_basis_tax_grid_reversal",
                'refund_method': 'refund',
                'journal_id': refund.journal_id.id,
            })
        reversed_refund = self.env['account.move'].browse(reversal_wizard.reverse_moves()['res_id'])

        self.assertRecordValues(reversed_refund.line_ids.sorted('balance'), [
            {'debit': 0.0,      'credit': 1000.0,   'tax_tag_ids': [],  'account_id': self.company_data['default_account_revenue'].id},
            {'debit': 0.0,      'credit': 333.33,   'tax_tag_ids': [],  'account_id': self.cash_basis_transfer_account.id},
            {'debit': 1333.33,  'credit': 0.0,      'tax_tag_ids': [],  'account_id': self.company_data['default_account_receivable'].id},
        ])

    def test_reconcile_cash_basis_tax_grid_multi_taxes(self):
        ''' Test the tax grid when reconciling an invoice with multiple taxes/tax repartition. '''
        self.env.company.tax_exigibility = True
        base_taxes = self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount
        base_tags = self.tax_tags[0] + self.tax_tags[4]

        # An invoice with 2 taxes:
        invoice_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'line_ids': [
                # Base Tax line
                (0, 0, {
                    'debit': 0.0,
                    'credit': 100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, base_taxes.ids)],
                }),

                # Tax lines
                (0, 0, {
                    'debit': 0.0,
                    'credit': 33.33,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),
                (0, 0, {
                    'debit': 0.0,
                    'credit': 0.01,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': self.cash_basis_tax_tiny_amount.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                (0, 0, {
                    'debit': 133.34,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        # A payment paying the full invoice amount.
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 133.34,   'account_id': self.extra_receivable_account_1.id}),
                (0, 0, {'debit': 133.34,    'credit': 0.0,      'account_id': self.company_data['default_account_revenue'].id}),
            ]
        })

        (invoice_move + payment_move).action_post()

        receivable_lines = (invoice_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        res = receivable_lines.reconcile()

        self.assertFullReconcile(res['full_reconcile'], receivable_lines)
        self.assertEqual(len(res.get('tax_cash_basis_moves', [])), 1)

        self.assertRecordValues(res['tax_cash_basis_moves'].line_ids, [
            # Base amount x 2 because there is two taxes:
            {'debit': 100.0,    'credit': 0.0,      'tax_ids': [],              'tax_tag_ids': [],                      'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 100.0,    'tax_ids': base_taxes.ids,  'tax_tag_ids': base_tags.ids,           'account_id': self.cash_basis_base_account.id},
            # tax_1:
            {'debit': 33.33,    'credit': 0.0,      'tax_ids': [],              'tax_tag_ids': [],                      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 33.33,    'tax_ids': [],              'tax_tag_ids': self.tax_tags[1].ids,    'account_id': self.tax_account_1.id},
            # tax_2:
            {'debit': 0.01,     'credit': 0.0,      'tax_ids': [],              'tax_tag_ids': [],                      'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.01,     'tax_ids': [],              'tax_tag_ids': self.tax_tags[5].ids,    'account_id': self.tax_account_2.id},
        ])

    def test_caba_mix_reconciliation(self):
        """ Test the reconciliation of tax lines (when using a reconcilable tax account)
        for cases mixing taxes exigible on payment and on invoices.
        """

        # Make the tax account reconcilable
        self.tax_account_1.reconcile = True
        self.env.company.tax_exigibility = True

        # Create a tax using the same accounts as the CABA one
        non_caba_tax = self.env['account.tax'].create({
            'name': 'tax 20%',
            'type_tax_use': 'purchase',
            'company_id': self.company_data['company'].id,
            'amount': 20,
            'tax_exigibility': 'on_invoice',
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': self.tax_account_1.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': self.tax_account_1.id,
                }),
            ],
        })

        # Create an invoice with a non-CABA tax
        non_caba_inv = self.init_invoice('in_invoice', amounts=[1000], post=True, taxes=non_caba_tax)

        # Create an invoice with a CABA tax using the same tax account and pay it
        caba_inv = self.init_invoice('in_invoice', amounts=[300], post=True, taxes=self.cash_basis_tax_a_third_amount)

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=caba_inv.ids).create({
            'payment_date': caba_inv.date,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        pmt_wizard._create_payments()

        partial_rec = caba_inv.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        # Create a misc operation with a line on the tax account, for full reconcile of those tax lines
        misc_move = self.env['account.move'].create({
            'name': "Misc move",
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'line 1',
                    'account_id': self.tax_account_1.id,
                    'credit': 300,
                }),
                (0, 0, {
                    'name': 'line 2',
                    'account_id': self.company_data['default_account_expense'].id, # Whatever the account here
                    'debit': 300,
                })
            ],
        })

        misc_move.action_post()

        lines_to_reconcile = (misc_move + caba_move + non_caba_inv).mapped('line_ids').filtered(lambda x: x.account_id == self.tax_account_1)
        lines_to_reconcile.reconcile()

        # Check full reconciliation
        self.assertTrue(all(line.full_reconcile_id for line in lines_to_reconcile), "All tax lines should be fully reconciled")

    def test_caba_double_tax(self):
        """ Test the CABA entries generated from an invoice with almost
        equal lines, different only on analytic accounting
        """
        # Make the tax account reconcilable
        self.tax_account_1.reconcile = True
        self.env.company.tax_exigibility = True

        # Create an invoice with a CABA tax using 'Include in analytic cost'
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice', account_predictive_bills_disable_prediction=True))
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.partner_id = self.partner_a
        self.cash_basis_tax_a_third_amount.analytic = True
        test_analytic_account = self.env['account.analytic.account'].create({'name': 'test_analytic_account'})

        tax = self.cash_basis_tax_a_third_amount

        # line with analytic account, will generate 2 lines in CABA move
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = "test line with analytic account"
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax)
            line_form.analytic_account_id = test_analytic_account
            line_form.price_unit = 100

        # line with analytic account, will generate other 2 lines in CABA move
        # even if the tax is the same
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = "test line"
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax)
            line_form.price_unit = 100

        rslt = move_form.save()
        rslt.action_post()

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=rslt.ids).create({
            'amount': rslt.amount_total,
            'payment_date': rslt.date,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        pmt_wizard._create_payments()

        partial_rec = rslt.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        self.assertEqual(len(caba_move.line_ids), 4, "All lines should be there")
        self.assertEqual(caba_move.line_ids.filtered(lambda x: x.tax_line_id).balance, 66.66, "Tax amount should take into account both lines")

    def test_caba_double_tax_negative_line(self):
        """ Tests making a cash basis invoice with 2 lines using the same tax: a positive and a negative one.
        """
        self.env.company.tax_exigibility = True
        invoice = self.init_invoice('in_invoice', amounts=[300, -60], post=True, taxes=self.cash_basis_tax_a_third_amount)

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 320,
            'payment_date': invoice.date,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        pmt_wizard._create_payments()

        partial_rec = invoice.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        self.assertRecordValues(caba_move.line_ids.sorted(lambda line: (-abs(line.balance), -line.debit, line.account_id)), [
            # Base amount:
            {'debit': 240.0,    'credit': 0.0,      'tax_tag_ids': self.tax_tags[0].ids,    'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 240.0,    'tax_tag_ids': [],                      'account_id': self.cash_basis_base_account.id},
            # tax:
            {'debit': 80.0,     'credit': 0.0,      'tax_tag_ids': self.tax_tags[1].ids,    'account_id': self.tax_account_1.id},
            {'debit': 0.0,      'credit': 80.0,     'tax_tag_ids': [],                      'account_id': self.cash_basis_transfer_account.id},
        ])

    def test_caba_dest_acc_reconciliation_partial_pmt(self):
        """ Test the reconciliation of tax lines (when using a reconcilable tax account)
        for partially paid invoices with cash basis taxes.
        This test is especially useful to check the implementation of the use case tested by
        test_reconciliation_cash_basis_foreign_currency_low_values does not have unwanted side effects.
        """

        # Make the tax account reconcilable
        self.tax_account_1.reconcile = True
        self.env.company.tax_exigibility = True

        # Create an invoice with a CABA tax using the same tax account and pay half of it
        caba_inv = self.init_invoice('in_invoice', amounts=[900], post=True, taxes=self.cash_basis_tax_a_third_amount)

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=caba_inv.ids).create({
            'amount': 600,
            'payment_date': caba_inv.date,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        pmt_wizard._create_payments()

        partial_rec = caba_inv.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        # Create a misc operation with a line on the tax account, for full reconcile with the tax line
        misc_move = self.env['account.move'].create({
            'name': "Misc move",
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'line 1',
                    'account_id': self.tax_account_1.id,
                    'credit': 150,
                }),
                (0, 0, {
                    'name': 'line 2',
                    'account_id': self.company_data['default_account_expense'].id, # Whatever the account here
                    'debit': 150,
                })
            ],
        })

        misc_move.action_post()

        lines_to_reconcile = (misc_move + caba_move).mapped('line_ids').filtered(lambda x: x.account_id == self.tax_account_1)
        lines_to_reconcile.reconcile()

        # Check full reconciliation
        self.assertTrue(all(line.full_reconcile_id for line in lines_to_reconcile), "All tax lines should be fully reconciled")

    def test_caba_undo_reconciliation(self):
        ''' Make sure there is no traceback like "Record has already been deleted" during the deletion of partials. '''
        self.cash_basis_transfer_account.reconcile = True

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'line',
                'account_id': self.company_data['default_account_expense'].id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
            })],
        })
        bill.action_post()

        # Register a payment creating the CABA journal entry on the fly and reconcile it with the tax line.
        self.env['account.payment.register']\
            .with_context(active_ids=bill.ids, active_model='account.move')\
            .create({})\
            ._create_payments()

        bill.button_draft()

    def test_caba_foreign_vat(self):
        self.env.company.tax_exigibility = True

        test_country = self.env['res.country'].create({
            'name': "Bretonnia",
            'code': 'wh',
        })

        foreign_vat_fpos = self.env['account.fiscal.position'].create({
            'name': "Fiscal Position to the Holy Grail",
            'country_id': test_country.id,
            'foreign_vat': 'WH1234',
        })

        foreign_caba_tax = self.env['account.tax'].create({
            'name': 'tax_1',
            'amount': 33.3333,
            'company_id': self.company_data['company'].id,
            'cash_basis_transition_account_id': self.cash_basis_transfer_account.id,
            'tax_exigibility': 'on_payment',
            'country_id': test_country.id,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                }),
            ],
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2021-07-01',
            'fiscal_position_id': foreign_vat_fpos.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "test",
                    'price_unit': 100,
                    'tax_ids': [Command.set(foreign_caba_tax.ids)],
                }),
            ]
        })
        invoice.action_post()

        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'payment_date': invoice.date,
        })._create_payments()

        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)])

        self.assertEqual(caba_move.fiscal_position_id, foreign_vat_fpos, "The foreign VAT fiscal position should be kept in the the cash basis move.")

    def test_caba_tax_group(self):
        """ Test the CABA entries generated from an invoice with
        a tax group
        """
        self.env.company.tax_exigibility = True

        # Make the tax account reconcilable
        self.tax_account_1.reconcile = True

        # Create an invoice with a CABA tax using 'Include in analytic cost'
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice', account_predictive_bills_disable_prediction=True))
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.partner_id = self.partner_a

        tax_a = self.cash_basis_tax_a_third_amount
        tax_b = self.cash_basis_tax_tiny_amount

        tax_group = self.env['account.tax'].create({
            'name': 'tax group',
            'amount_type': 'group',
            'company_id': self.company_data['company'].id,
            'children_tax_ids': [Command.set([tax_a.id, tax_b.id])],
        })

        # line with analytic account, will generate 2 lines in CABA move
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'move_type': 'entry',
            'line_ids': [
                # Base Tax line
                Command.create({
                    'debit': 0.0,
                    'credit': 3000.0,
                    'amount_currency': 3000.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(tax_group.ids)],
                }),

                # Tax line A
                Command.create({
                    'debit': 0.0,
                    'credit': 1000.0,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': tax_a.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Tax line B
                Command.create({
                    'debit': 0.0,
                    'credit': 1.0,
                    'account_id': self.cash_basis_transfer_account.id,
                    'tax_repartition_line_id': tax_b.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'tax').id,
                }),

                # Receivable lines
                Command.create({
                    'debit': 4001.0,
                    'credit': 0.0,
                    'account_id': self.extra_receivable_account_1.id,
                }),
            ]
        })

        invoice.action_post()

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({})
        pmt_wizard._create_payments()

        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)])
        self.assertEqual(len(caba_move.line_ids), 6, "All lines should be there")
        tax_group_base_tags = (tax_a | tax_b).invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'base').tag_ids.ids
        tax_a_tax_tag = tax_a.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').tag_ids.ids
        tax_b_tax_tag = tax_b.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').tag_ids.ids
        self.assertRecordValues(caba_move.line_ids, [
            {'balance':  3000.0, 'tax_line_id':    False, 'tax_tag_ids':                  [], 'tax_ids':                  []},
            {'balance': -3000.0, 'tax_line_id':    False, 'tax_tag_ids': tax_group_base_tags, 'tax_ids': (tax_a | tax_b).ids},
            {'balance':  1000.0, 'tax_line_id':    False, 'tax_tag_ids':                  [], 'tax_ids':                  []},
            {'balance': -1000.0, 'tax_line_id': tax_a.id, 'tax_tag_ids':       tax_a_tax_tag, 'tax_ids':                  []},
            {'balance':     1.0, 'tax_line_id':    False, 'tax_tag_ids':                  [], 'tax_ids':                  []},
            {'balance':    -1.0, 'tax_line_id': tax_b.id, 'tax_tag_ids':       tax_b_tax_tag, 'tax_ids':                  []},
        ])
        # No exchange journal entry created for CABA.
        exchange_difference_move = invoice.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable').full_reconcile_id.exchange_move_id
        self.assertFalse(exchange_difference_move)

    def test_cash_basis_taxline_without_account(self):
        """
        Make sure that cash basis taxlines that don't have an account are handled properly.
        """
        self.env.company.tax_exigibility = True

        tax = self.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': self.cash_basis_transfer_account.id,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                (0, 0, {
                    'factor_percent': 40,
                    'account_id': self.tax_account_1.id,
                    'repartition_type': 'tax',
                }),

                (0, 0, {
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                (0, 0, {
                    'factor_percent': 40,
                    'account_id': self.tax_account_1.id,
                    'repartition_type': 'tax',
                }),

                (0, 0, {
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                }),
            ],
        })

        # create invoice
        move_form = Form(self.env['account.move'].with_context(
            default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax)
        invoice = move_form.save()
        invoice.action_post()

        # make payment
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()

        # check caba move
        partial_rec = invoice.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search(
            [('tax_cash_basis_rec_id', '=', partial_rec.id)])
        expected_values = [
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 0.0,
                'credit': 800.0
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 800.0,
                'credit': 0.0
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 0.0,
                'credit': 64.0
            },
            {
                'account_id': self.tax_account_1.id,
                'debit': 64.0,
                'credit': 0.0},
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 0.0,
                'credit': 96.0
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 96.0,
                'credit': 0.0
            }
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)

    def test_cash_basis_full_refund(self):
        """ Ensure the caba entry and the exchange difference journal entry for caba are not created in case of full
        refund.
        """
        self.env.company.tax_exigibility = True

        tax = self.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': self.cash_basis_transfer_account.id,
        })

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000.0], taxes=tax)

        # Reverse completely the invoice.
        credit_note_wizard = self.env['account.move.reversal']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create({
                'refund_method': 'cancel',
                'reason': 'test_cash_basis_full_refund',
                'journal_id': invoice.journal_id.id,
        })
        action_values = credit_note_wizard.reverse_moves()
        self.assertRecordValues(invoice, [{'payment_state': 'reversed'}])

        # Check no CABA move has been created.
        cash_basis_moves = self.env['account.move']\
            .search([('tax_cash_basis_origin_move_id', 'in', (invoice.id, action_values['res_id']))])
        self.assertFalse(cash_basis_moves)

        # No exchange journal entry created for CABA.
        caba_transfer_amls = self.env['account.move.line'].search([
            ('account_id', '=', self.cash_basis_transfer_account.id),
            ('move_id', 'not in', (invoice.id, action_values['res_id'])),
        ])
        self.assertFalse(caba_transfer_amls.move_id)
