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

        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.extra_receivable_account_1 = cls.copy_account(cls.receivable_account)
        cls.extra_receivable_account_2 = cls.copy_account(cls.receivable_account)
        cls.extra_payable_account_1 = cls.copy_account(cls.company_data['default_account_payable'])
        cls.extra_payable_account_2 = cls.copy_account(cls.company_data['default_account_payable'])

        cls.exch_income_account = cls.env.company.income_currency_exchange_account_id
        cls.exch_expense_account = cls.env.company.expense_currency_exchange_account_id

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
            'account_type': 'income',
            'company_id': cls.company_data['company'].id,
        })
        cls.company_data['company'].account_cash_basis_base_account_id = cls.cash_basis_base_account

        cls.cash_basis_transfer_account = cls.env['account.account'].create({
            'code': 'cash_basis_transfer_account',
            'name': 'cash_basis_transfer_account',
            'account_type': 'income',
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_1 = cls.env['account.account'].create({
            'code': 'tax_account_1',
            'name': 'tax_account_1',
            'account_type': 'income',
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_2 = cls.env['account.account'].create({
            'code': 'tax_account_2',
            'name': 'tax_account_2',
            'account_type': 'income',
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
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[0].ids)],
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_1.id,
                    'tag_ids': [(6, 0, cls.tax_tags[1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[2].ids)],
                }),

                (0, 0, {
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
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[4].ids)],
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account_2.id,
                    'tag_ids': [(6, 0, cls.tax_tags[5].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, cls.tax_tags[6].ids)],
                }),

                (0, 0, {
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

    def assertFullReconcileAccount(self, full_reconcile, account):
        self.assertFullReconcile(full_reconcile, self.env['account.move.line'].search([('account_id', '=', account.id)]))

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

    def _create_line_for_reconciliation(self, balance, amount_currency, currency, move_date):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': move_date,
            'line_ids': [
                Command.create({
                    'debit': balance if balance > 0.0 else 0.0,
                    'credit': -balance if balance < 0.0 else 0.0,
                    'amount_currency': amount_currency,
                    'account_id': self.receivable_account.id,
                    'currency_id': currency.id,
                }),
                Command.create({
                    'debit': -balance if balance < 0.0 else 0.0,
                    'credit': balance if balance > 0.0 else 0.0,
                    'amount_currency': -amount_currency,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': currency.id,
                }),
            ],
        })
        move.action_post()
        line = move.line_ids.filtered(lambda x: x.account_id == self.receivable_account)

        self.assertRecordValues(line, [{
            'amount_residual': balance,
            'amount_residual_currency': amount_currency,
            'reconciled': False,
        }])

        return line

    def test_full_reconcile_bunch_lines(self):
        """ Test the reconciliation with multiple lines at the same time and ensure the result is always a full
        reconcile whatever the number of involved currencies.
        """
        comp_curr = self.company_data['currency']
        foreign_curr1 = self.currency_data['currency']
        foreign_curr2 = self.currency_data_2['currency']

        line_1 = self._create_line_for_reconciliation(1000.0, 1000.0, comp_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-300.0, -300.0, comp_curr, '2016-01-01')
        line_3 = self._create_line_for_reconciliation(-400.0, -400.0, comp_curr, '2016-01-01')
        line_4 = self._create_line_for_reconciliation(-500.0, -500.0, comp_curr, '2016-01-01')
        line_5 = self._create_line_for_reconciliation(200.0, 200.0, comp_curr, '2016-01-01')
        comp_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        line_1 = self._create_line_for_reconciliation(1200.0, 3600.0, foreign_curr1, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-240.0, -480.0, foreign_curr1, '2017-01-01')
        line_3 = self._create_line_for_reconciliation(-720.0, -1440.0, foreign_curr1, '2017-01-01')
        line_4 = self._create_line_for_reconciliation(-1020.0, -2040.0, foreign_curr1, '2017-01-01')
        line_5 = self._create_line_for_reconciliation(120.0, 360.0, foreign_curr1, '2016-01-01')
        same_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        line_1 = self._create_line_for_reconciliation(1200.0, 3600.0, foreign_curr1, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(780.0, 2340.0, foreign_curr1, '2016-01-01')
        line_3 = self._create_line_for_reconciliation(-240.0, -960.0, foreign_curr2, '2017-01-01')
        line_4 = self._create_line_for_reconciliation(-720.0, -2880.0, foreign_curr2, '2017-01-01')
        line_5 = self._create_line_for_reconciliation(-1020.0, -4080.0, foreign_curr2, '2017-01-01')
        multi_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        for batch, sub_test_name in (
                (comp_curr_batch, "Batch in company currency"),
                (same_curr_batch, "Batch in foreign currency"),
                (multi_curr_batch, "Batch with multiple currencies"),
                (comp_curr_batch + same_curr_batch + multi_curr_batch, "All batches"),
        ):
            with self.subTest(sub_test_name=sub_test_name):

                res = batch.reconcile()
                self.assertTrue(res.get('full_reconcile'))
                self.assertRecordValues(
                    batch,
                    [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(batch),
                )
                batch.remove_move_reconcile()

    def test_reconcile_lines_multiple_in_foreign_currency(self):
        currency = self.currency_data['currency']

        rates = (1/3, 1/2)
        for rate1 in rates:
            for rate2 in rates:
                for rate3 in rates:
                    with self.subTest(rate1=rate1, rate2=rate2, rate3=rate3):
                        line_1 = self._create_line_for_reconciliation(120.0 * rate1, 120.0, currency, '2017-01-01')
                        line_2 = self._create_line_for_reconciliation(120.0 * rate2, 120.0, currency, '2017-01-01')
                        line_3 = self._create_line_for_reconciliation(-240.0 * rate3, -240.0, currency, '2017-01-01')

                        (line_1 + line_2 + line_3).reconcile()
                        self.assertTrue(line_1.full_reconcile_id)

    def test_reverse_exchange_difference(self):
        """ Test the reversing of the exchange difference to ensure there is no unexpected recursion inside the
        'reconcile' method.
        """
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        for line1_vals, line2_vals in (
                ((60.0, 120.0, foreign_curr, '2017-01-01'), (-40.0, -120.0, foreign_curr, '2016-01-01')),
                ((-60.0, -120.0, foreign_curr, '2017-01-01'), (40.0, 120.0, foreign_curr, '2016-01-01')),
                ((60.0, 60.0, comp_curr, '2017-01-01'), (-40.0, -120.0, foreign_curr, '2016-01-01')),
                ((-60.0, -60.0, comp_curr, '2017-01-01'), (40.0, 120.0, foreign_curr, '2016-01-01')),
        ):
            line1 = self._create_line_for_reconciliation(*line1_vals)
            line2 = self._create_line_for_reconciliation(*line2_vals)
            with self.subTest(line1_vals=line1_vals, line2_vals=line2_vals):

                res = (line1 + line2).reconcile()

                # Reconcile.
                # Don't check the result since this is already checked by another tests.
                exchange_diff = res['partials'].exchange_move_id
                self.assertTrue(exchange_diff)

                # Unreconcile.
                # A reversal is created to cancel the exchange difference journal entry.
                line1.remove_move_reconcile()
                reverse_exchange_diff_lines = exchange_diff.line_ids.matched_debit_ids.debit_move_id \
                                              + exchange_diff.line_ids.matched_credit_ids.credit_move_id
                reverse_exchange_diff = reverse_exchange_diff_lines.move_id
                self.assertTrue(reverse_exchange_diff)

                self.assertRecordValues(exchange_diff.line_ids + reverse_exchange_diff.line_ids, [
                    {'reconciled': True},
                    {'reconciled': False},
                    {'reconciled': True},
                    {'reconciled': False},
                ])

    def test_reconcile_lines_corner_case_1_zero_balance_same_foreign_currency(self):
        """ Test the reconciliation of lines having a zero balance but the same foreign currency. """
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(0.0, -0.01, currency, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(0.0, 0.02, currency, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 0.0,
            'debit_amount_currency': 0.01,
            'credit_amount_currency': 0.01,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
            'exchange_move_id': None,
        }])
        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['full_reconcile'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -0.01,
                'currency_id': currency.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 0.01,
                'currency_id': currency.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 0.0,
            'debit_amount_currency': 0.01,
            'credit_amount_currency': 0.01,
            'debit_move_id': line_2.id,
            'credit_move_id': res['full_reconcile'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_lines_corner_case_2_zero_amount_currency_same_foreign_currency(self):
        """ Test a corner case when both lines have something to reconcile in company currency but nothing
        in foreign currency. It could be due to:
        - a bad usage of the `no_exchange_difference` context key
        - a partial reconciliation made before migrating to this version
        - some rounding error when dealing with currencies having != decimal places
        - strange journal items made by the user
        """
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-0.01, 0.0, currency, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(0.02, 0.0, currency, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 0.01,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
            'exchange_move_id': None,
        }])
        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['full_reconcile'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 0.01,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.01,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 0.01,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['full_reconcile'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_lines_corner_case_3_zero_balance_one_foreign_currency(self):
        """ Test the special case when one line (credit) has a zero residual amount in company currency probably due to
        some rounding issues or accumulated rounding due to multiple reconciliations.
        This line is matched with another line (debit) using the company currency.
        """
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-0.01, -0.01, comp_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(0.0, 0.03, foreign_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 0.0,
            'debit_amount_currency': 0.02,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.01,
                'credit': 0.0,
                'amount_currency': 0.01,
                'currency_id': comp_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.01,
                'amount_currency': -0.01,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['full_reconcile'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': -0.01,
                'currency_id': foreign_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.0,
                'amount_currency': 0.01,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [
            {
                'amount': 0.01,
                'debit_amount_currency': 0.01,
                'credit_amount_currency': 0.01,
                'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 0.0,
                'debit_amount_currency': 0.01,
                'credit_amount_currency': 0.01,
                'debit_move_id': line_2.id,
                'credit_move_id': res['full_reconcile'].exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_lines_corner_case_4_zero_amount_currency_multiple_currencies(self):
        foreign_curr1 = self.currency_data['currency']
        foreign_curr2 = self.currency_data_2['currency']

        line_1 = self._create_line_for_reconciliation(-0.01, 0.0, foreign_curr2, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(0.01, 0.03, foreign_curr1, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 0.01,
            'debit_amount_currency': 0.03,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
            'exchange_move_id': None,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_expense_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(60.0, 120.0, currency, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-80.0, -240.0, currency, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_1.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -40.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_income_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(40.0, 120.0, currency, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-120.0, -240.0, currency, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -60.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_expense_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-40.0, -120.0, currency, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(120.0, 240.0, currency, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 60.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_income_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -120.0, currency, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(80.0, 240.0, currency, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 40.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(60.0, 120.0, foreign_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-80.0, -80.0, comp_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_1.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -40.0,      'amount_residual_currency': -40.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(60.0, 60.0, comp_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-80.0, -240.0, foreign_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': line_1.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -40.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(40.0, 120.0, foreign_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-120.0, -120.0, comp_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -60.0,      'amount_residual_currency': -60.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(40.0, 40.0, comp_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-120.0, -240.0, foreign_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -60.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-40.0, -120.0, foreign_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(120.0, 120.0, comp_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 60.0,       'amount_residual_currency': 60.0,   'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-40.0, -40.0, comp_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(120.0, 240.0, foreign_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 60.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -60.0, comp_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(80.0, 240.0, foreign_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 40.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(80.0, 80.0, comp_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 40.0,       'amount_residual_currency': 40.0,   'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_expense_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(60.0, 120.0, currency, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-40.0, -120.0, currency, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_1.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_income_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(40.0, 120.0, currency, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-60.0, -120.0, currency, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_expense_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-40.0, -120.0, currency, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(60.0, 120.0, currency, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_income_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -120.0, currency, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(40.0, 120.0, currency, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': currency.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(60.0, 120.0, foreign_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-40.0, -40.0, comp_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_1.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(60.0, 60.0, comp_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-40.0, -120.0, foreign_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': line_1.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(40.0, 120.0, foreign_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-60.0, -60.0, comp_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(40.0, 40.0, comp_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_1.id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_2.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-40.0, -40.0, comp_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(60.0, 120.0, foreign_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-40.0, -120.0, foreign_curr, '2016-01-01')
        line_2 = self._create_line_for_reconciliation(60.0, 60.0, comp_curr, '2017-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': line_2.account_id.id,
            },
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_expense_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': line_2.id,
            'credit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -60.0, comp_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(40.0, 120.0, foreign_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 40.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 20.0,
                'currency_id': comp_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': -20.0,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 20.0,
            'credit_amount_currency': 20.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(40.0, 40.0, comp_curr, '2016-01-01')

        res = (line_1 + line_2).reconcile()

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': False}])
        self.assertRecordValues(res['partials'], [{
            'amount': 40.0,
            'debit_amount_currency': 40.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2017-01-01')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 20.0,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': line_1.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 20.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 20.0,
            'debit_amount_currency': 0.0,
            'credit_amount_currency': 0.0,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': line_1.id,
        }])
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
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
                    'currency_id': self.currency_data['currency'].id,
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

        lines_to_reconcile = move.line_ids.filtered(lambda x: (x.account_id.reconcile or x.account_id.account_type in ('asset_cash', 'liability_credit_card')) and not x.reconciled)

        self.assertRecordValues(lines_to_reconcile, [
            {'debit': 1200.0, 'credit': 0.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 200.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 400.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 600.0, 'reconciled': False},
        ])

        reversed_move = move._reverse_moves(cancel=True)

        reversed_lines = reversed_move.line_ids.filtered(lambda x: (
                x.account_id.reconcile or x.account_id.account_type in ('asset_cash', 'liability_credit_card')
        ))

        self.assertRecordValues(reversed_lines, [
            {'debit': 0.0, 'credit': 1200.0, 'reconciled': True},
            {'debit': 200.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 400.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 600.0, 'credit': 0.0, 'reconciled': True},
        ])

        self.assertTrue(all([line.full_reconcile_id for line in reversed_lines]))

    def test_reconcile_special_mexican_workflow_1(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.env['res.currency'].create({
            'name': "Sushi",
            'symbol': '🍣',
            'rounding': 0.01,
            'rate_ids': [
                Command.create({'name': '2019-09-24', 'rate': 0.050800000000}),
                Command.create({'name': '2019-06-28', 'rate': 0.052235000000}),
                Command.create({'name': '2019-06-24', 'rate': 0.052686000000}),
                Command.create({'name': '2019-06-20', 'rate': 0.052353000000}),
                Command.create({'name': '2019-06-12', 'rate': 0.052072000000}),
            ],
        })

        refund1 = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2019-06-12',
            'date': '2019-06-12',
            'partner_id': self.partner_a.id,
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1385.92,
                'tax_ids': [],
            })],
        })
        refund1.action_post()
        refund1_rec_line = refund1.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        inv1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-06-20',
            'date': '2019-06-20',
            'partner_id': self.partner_a.id,
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 839.40,
                'tax_ids': [],
            })],
        })
        inv1.action_post()
        inv1_rec_line = inv1.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        inv2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-06-24',
            'date': '2019-06-24',
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1935.72,
                'tax_ids': [],
            })],
        })
        inv2.action_post()
        inv2_rec_line = inv2.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        pay1 = self.env['account.payment'].create({
            'partner_type': 'customer',
            'payment_type': 'inbound',
            'date': '2019-06-28',
            'amount': 1907.17,
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
        })
        pay1_liquidity_line = pay1.line_ids.filtered(lambda x: x.account_id.account_type != 'asset_receivable')
        pay1_rec_line = pay1.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        pay1.action_post()
        pay1.write({'line_ids': [
            Command.update(pay1_liquidity_line.id, {'debit': 36511.34}),
            Command.update(pay1_rec_line.id, {'credit': 36511.34}),
        ]})

        pay2 = self.env['account.payment'].create({
            'partner_type': 'customer',
            'payment_type': 'inbound',
            'date': '2019-09-24',
            'amount': 0.09,
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
        })
        pay2.action_post()
        pay2_rec_line = pay2.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        # 1st reconciliation refund1 + inv1
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {
            inv1.id: 839.40,
            inv2.id: 36740.69,
        })
        self.assertRecordValues(refund1_rec_line + inv1_rec_line, [
            {'amount_residual': -1385.92,   'amount_residual_currency': -1385.92,   'reconciled': False},
            {'amount_residual': 839.40,     'amount_residual_currency': 839.40,     'reconciled': False},
        ])

        res = (refund1_rec_line + inv1_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 839.4,
            'debit_amount_currency': 839.4,
            'credit_amount_currency': 839.4,
            'debit_move_id': inv1_rec_line.id,
            'credit_move_id': refund1_rec_line.id,
            'exchange_move_id': None,
        }])
        self.assertRecordValues(refund1_rec_line + inv1_rec_line, [
            {'amount_residual': -546.52,    'amount_residual_currency': -546.52,    'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])
        self.assert_invoice_outstanding_reconciled_widget(refund1, {
            inv1.id: 839.40,
        })

        # 2th reconciliation refund1 + inv2
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {
            inv2.id: 36740.69,
        })
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': -546.52,    'amount_residual_currency': -546.52,    'reconciled': False},
            {'amount_residual': 36740.69,   'amount_residual_currency': 1935.72,    'reconciled': False},
        ])

        res = (refund1_rec_line + inv2_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 540.18,
            'debit_amount_currency': 28.46,
            'credit_amount_currency': 540.18,
            'debit_move_id': inv2_rec_line.id,
            'credit_move_id': refund1_rec_line.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2019-06-24')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 6.34,
                'credit': 0.0,
                'amount_currency': 6.34,
                'currency_id': comp_curr.id,
                'account_id': refund1_rec_line.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 6.34,
                'amount_currency': -6.34,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 6.34,
            'debit_amount_currency': 6.34,
            'credit_amount_currency': 6.34,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': refund1_rec_line.id,
        }])
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 36200.51,   'amount_residual_currency': 1907.26,    'reconciled': False},
        ])
        self.assert_invoice_outstanding_reconciled_widget(refund1, {
            inv1.id: 839.40,
            inv2.id: 540.18,
            res['partials'].exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {})

        # 3th reconciliation inv1 + pay1
        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
        })
        self.assertRecordValues(inv2_rec_line + pay1_rec_line, [
            {'amount_residual': 36200.51,   'amount_residual_currency': 1907.26,    'reconciled': False},
            {'amount_residual': -36511.34,  'amount_residual_currency': -1907.17,   'reconciled': False},
        ])

        res = (inv2_rec_line + pay1_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 36198.80,
            'debit_amount_currency': 1907.17,
            'credit_amount_currency': 1907.17,
            'debit_move_id': inv2_rec_line.id,
            'credit_move_id': pay1_rec_line.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2019-06-28')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 312.54,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': pay1_rec_line.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 312.54,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(inv2_rec_line + pay1_rec_line, [
            {'amount_residual': 1.71,       'amount_residual_currency': 0.09,       'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(lambda x: x.id != res['partials'].id)

        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            res['partials'].exchange_move_id.id: 312.54,
            payment_exchange_id[0].exchange_move_id.id: 6.34,
        })

        # 4th reconciliation inv2 + pay2
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            pay2.move_id.id: 0.09,
        })
        self.assertRecordValues(inv2_rec_line + pay2_rec_line, [
            {'amount_residual': 1.71,       'amount_residual_currency': 0.09,       'reconciled': False},
            {'amount_residual': -1.77,      'amount_residual_currency': -0.09,      'reconciled': False},
        ])

        res = (inv2_rec_line + pay2_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 1.71,
            'debit_amount_currency': 0.09,
            'credit_amount_currency': 0.09,
            'debit_move_id': inv2_rec_line.id,
            'credit_move_id': pay2_rec_line.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2019-09-24')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.06,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': inv2_rec_line.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.06,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(inv2_rec_line + pay2_rec_line, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(lambda x: x.id != res['partials'].id)

        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
            res['partials'].exchange_move_id.id: 0.06,
            payment_exchange_id[0].exchange_move_id.id: 6.34,
            payment_exchange_id[1].exchange_move_id.id: 312.54,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {})

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': None}])

    def test_reconcile_special_mexican_workflow_2(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.env['res.currency'].create({
            'name': "Sushi",
            'symbol': '🍣',
            'rounding': 0.01,
            'rate_ids': [
                Command.create({'name': '2019-09-24', 'rate': 0.050800000000}),
                Command.create({'name': '2019-06-28', 'rate': 0.052235000000}),
                Command.create({'name': '2019-06-24', 'rate': 0.052686000000}),
                Command.create({'name': '2019-06-20', 'rate': 0.052353000000}),
                Command.create({'name': '2019-06-12', 'rate': 0.052072000000}),
            ],
        })

        refund1 = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2019-06-12',
            'date': '2019-06-12',
            'partner_id': self.partner_a.id,
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1385.92,
                'tax_ids': [],
            })],
        })
        refund1.action_post()
        refund1_rec_line = refund1.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        inv1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-06-20',
            'date': '2019-06-20',
            'partner_id': self.partner_a.id,
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 839.40,
                'tax_ids': [],
            })],
        })
        inv1.action_post()
        inv1_rec_line = inv1.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        inv2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-06-24',
            'date': '2019-06-24',
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1935.72,
                'tax_ids': [],
            })],
        })
        inv2.action_post()
        inv2_rec_line = inv2.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        pay1 = self.env['account.payment'].create({
            'partner_type': 'customer',
            'payment_type': 'inbound',
            'date': '2019-06-28',
            'amount': 1907.17,
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
        })
        pay1_liquidity_line = pay1.line_ids.filtered(lambda x: x.account_id.account_type != 'asset_receivable')
        pay1_rec_line = pay1.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        pay1.action_post()
        pay1.write({'line_ids': [
            Command.update(pay1_liquidity_line.id, {'debit': 36511.34}),
            Command.update(pay1_rec_line.id, {'credit': 36511.34}),
        ]})

        pay2 = self.env['account.payment'].create({
            'partner_type': 'customer',
            'payment_type': 'inbound',
            'date': '2019-09-24',
            'amount': 0.09,
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
        })
        pay2.action_post()
        pay2_rec_line = pay2.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')

        self.assertRecordValues(refund1_rec_line + inv1_rec_line + inv2_rec_line + pay1_rec_line + pay2_rec_line, [
            {'amount_residual': -1385.92,   'amount_residual_currency': -1385.92},
            {'amount_residual': 839.40,     'amount_residual_currency': 839.40},
            {'amount_residual': 36740.69,   'amount_residual_currency': 1935.72},
            {'amount_residual': -36511.34,  'amount_residual_currency': -1907.17},
            {'amount_residual': -1.77,      'amount_residual_currency': -0.09},
        ])

        # 1st reconciliation refund1 + inv1
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {
            inv1.id: 839.40,
            inv2.id: 36740.69,
        })
        self.assertRecordValues(refund1_rec_line + inv1_rec_line, [
            {'amount_residual': -1385.92,   'amount_residual_currency': -1385.92,   'reconciled': False},
            {'amount_residual': 839.40,     'amount_residual_currency': 839.40,     'reconciled': False},
        ])

        res = (refund1_rec_line + inv1_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 839.4,
            'debit_amount_currency': 839.4,
            'credit_amount_currency': 839.4,
            'debit_move_id': inv1_rec_line.id,
            'credit_move_id': refund1_rec_line.id,
            'exchange_move_id': None,
        }])
        self.assertRecordValues(refund1_rec_line + inv1_rec_line, [
            {'amount_residual': -546.52,    'amount_residual_currency': -546.52,    'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])
        self.assert_invoice_outstanding_reconciled_widget(refund1, {
            inv1.id: 839.40,
        })

        # 2th reconciliation refund1 + inv2
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
        })
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': -546.52,    'amount_residual_currency': -546.52,    'reconciled': False},
            {'amount_residual': 36740.69,   'amount_residual_currency': 1935.72,    'reconciled': False},
        ])

        res = (inv2_rec_line + pay1_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 36198.8,
            'debit_amount_currency': 1907.17,
            'credit_amount_currency': 1907.17,
            'debit_move_id': inv2_rec_line.id,
            'credit_move_id': pay1_rec_line.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2019-06-28')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 312.54,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': inv2_rec_line.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 312.54,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(inv2_rec_line + pay1_rec_line, [
            {'amount_residual': 541.89,     'amount_residual_currency': 28.55,      'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])
        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            pay1.move_id.id: 1907.17,
            res['partials'].exchange_move_id.id: 312.54,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            refund1.id: 28.46,
            pay2.move_id.id: 0.09,
        })

        # 3th reconciliation refund1 + inv2
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {
            inv2.id: 541.89,
        })
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': -546.52,    'amount_residual_currency': -546.52,    'reconciled': False},
            {'amount_residual': 541.89,     'amount_residual_currency': 28.55,      'reconciled': False},
        ])

        res = (refund1_rec_line + inv2_rec_line).reconcile()

        self.assertRecordValues(res['partials'], [{
            'amount': 540.18,
            'debit_amount_currency': 28.46,
            'credit_amount_currency': 540.18,
            'debit_move_id': inv2_rec_line.id,
            'credit_move_id': refund1_rec_line.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2019-06-24')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 6.34,
                'credit': 0.0,
                'amount_currency': 6.34,
                'currency_id': comp_curr.id,
                'account_id': refund1_rec_line.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 6.34,
                'amount_currency': -6.34,
                'currency_id': comp_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(res['exchange_partials'], [{
            'amount': 6.34,
            'debit_amount_currency': 6.34,
            'credit_amount_currency': 6.34,
            'debit_move_id': res['partials'].exchange_move_id.line_ids[0].id,
            'credit_move_id': refund1_rec_line.id,
        }])
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 1.71,       'amount_residual_currency': 0.09,       'reconciled': False},
        ])
        self.assert_invoice_outstanding_reconciled_widget(refund1, {
            inv1.id: 839.40,
            inv2.id: 540.18,
            res['partials'].exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {})

        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            pay2.move_id.id: 0.09,
        })

        res = (inv2_rec_line + pay2_rec_line).reconcile()
        self.assertRecordValues(res['partials'], [{
            'amount': 1.71,
            'debit_amount_currency': 0.09,
            'credit_amount_currency': 0.09,
            'debit_move_id': inv2_rec_line.id,
            'credit_move_id': pay2_rec_line.id,
        }])
        self.assertRecordValues(res['partials'].exchange_move_id, [{'date': fields.Date.from_string('2019-09-24')}])
        self.assertRecordValues(res['partials'].exchange_move_id.line_ids, [
            {
                'debit': 0.06,
                'credit': 0.0,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': inv2_rec_line.account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 0.06,
                'amount_currency': 0.0,
                'currency_id': foreign_curr.id,
                'account_id': self.exch_income_account.id,
            },
        ])
        self.assertRecordValues(inv2_rec_line + pay2_rec_line, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(lambda x: x.id != res['partials'].id)

        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
            res['partials'].exchange_move_id.id: 0.06,
            payment_exchange_id[0].exchange_move_id.id: 312.54,
            payment_exchange_id[1].exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {})

        self.assertTrue(res.get('full_reconcile'))
        self.assertRecordValues(res['full_reconcile'], [{'exchange_move_id': None}])

    def test_migration_to_new_reconciliation_same_foreign_currency(self):
        foreign_curr = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(80.0, 240.0, foreign_curr, '2016-01-01')

        # Create the partial as it should be created in previous version.
        self.env['account.partial.reconcile'].create({
            'amount': 60.0,
            'debit_amount_currency': 120.0,
            'credit_amount_currency': 120.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        })
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 20.0,       'amount_residual_currency': 120.0,      'reconciled': False},
        ])

        # Reconcile using the "new" reconciliation.
        line_3 = self._create_line_for_reconciliation(-15.0, -30.0, foreign_curr, '2017-01-01')
        (line_2 + line_3).reconcile()
        self.assertRecordValues(line_2 + line_3, [
            {'amount_residual': 10.0,       'amount_residual_currency': 90.0,       'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        line_4 = self._create_line_for_reconciliation(-30.0, -90.0, foreign_curr, '2016-01-01')
        (line_2 + line_4).reconcile()
        self.assertRecordValues(line_2 + line_4, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

    def test_migration_to_new_reconciliation_multiple_currencies_fix_residual_with_writeoff(self):
        comp_curr = self.company_data['currency']
        foreign_curr1 = self.currency_data['currency']

        line_1 = self._create_line_for_reconciliation(600.0, 1200.0, foreign_curr1, '2017-01-01')
        line_2 = self._create_line_for_reconciliation(-800.0, -2400.0, foreign_curr1, '2016-01-01')
        line_3 = self._create_line_for_reconciliation(400.0, 400.0, comp_curr, '2016-01-01')

        # Create the partials as it should be created in previous version.
        self.env['account.partial.reconcile'].create([
            {
                'amount': 600.0,
                'debit_amount_currency': 1200.0,
                'credit_amount_currency': 1200.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 200.0,
                'debit_amount_currency': 200.0,
                'credit_amount_currency': 600.0,
                'debit_move_id': line_3.id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(line_1 + line_2 + line_3, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': -600.0, 'reconciled': False},
            {'amount_residual': 200.0,      'amount_residual_currency': 200.0,  'reconciled': False},
        ])

        # Fix 'line_2' & 'line_4' using the "new" reconciliation.
        line_4 = self._create_line_for_reconciliation(0.0, 600.0, foreign_curr1, '2016-01-01')
        line_5 = self._create_line_for_reconciliation(-200.0, -200.0, comp_curr, '2016-01-01')
        (line_2 + line_3 + line_4 + line_5).reconcile()

        self.assertRecordValues(line_1 + line_2 + line_3 + line_4 + line_5, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
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
        self.cash_basis_tax_tiny_amount.amount = 0.01
        cash_basis_move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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
        cash_basis_move.line_ids.flush_model()

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

        currency_id = self.currency_data['currency'].id
        taxes = self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount

        cash_basis_move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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

        self.assertFullReconcileAccount(res['full_reconcile'], self.extra_receivable_account_1)
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

        self.assertFullReconcileAccount(res['full_reconcile'], self.extra_receivable_account_2)
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

        self.assertTrue(res.get('full_reconcile'))
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
        currency_id = self.setup_multi_currency_data(default_values={
            'name': 'bitcoin',
            'symbol': 'bc',
            'currency_unit_label': 'Bitcoin',
            'currency_subunit_label': 'Tiny bitcoin',
        }, rate2016=0.5, rate2017=0.66666666666666)['currency'].id

        # Rate 2/1 in 2016.
        caba_inv = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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

        receivable_line = caba_inv.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        self.assertTrue(receivable_line.full_reconcile_id, "Invoice should be fully paid")

        self.assertRecordValues(partial_rec.exchange_move_id.line_ids, [
            {'account_id': receivable_line.account_id.id,                                   'debit': 0.0,   'credit': 55.0, 'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': caba_move.company_id.expense_currency_exchange_account_id.id,    'debit': 55.0,  'credit': 0.0,  'amount_currency': 0.0, 'tax_ids': [],                                      'tax_line_id': False},
        ])

        exchange_move = receivable_line.full_reconcile_id.exchange_move_id
        self.assertTrue(exchange_move, "There should be an exchange difference move created")
        self.assertRecordValues(exchange_move.line_ids, [
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
        currency_id = self.setup_multi_currency_data(default_values={
            'name': 'bitcoin',
            'symbol': 'bc',
            'currency_unit_label': 'Bitcoin',
            'currency_subunit_label': 'Tiny bitcoin',
            'rounding': 0.01,
        }, rate2016=0.5, rate2017=0.66666666666666)['currency'].id

        # Rate 2/1 in 2016.
        caba_inv = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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

        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=caba_inv.ids)\
            .create({
                'payment_date': '2017-01-01',
                'currency_id': currency_id,
                'amount': 110.0,
            })\
            ._create_payments()

        receivable_line = caba_inv.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        partial_rec = caba_inv.line_ids.matched_credit_ids
        self.assertTrue(receivable_line.full_reconcile_id, "Invoice should be fully paid")

        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', caba_inv.line_ids.matched_credit_ids.ids)])
        self.assertRecordValues(caba_move.line_ids, [
            {'account_id': self.cash_basis_base_account.id,     'debit': 150.0,     'credit': 0.0,      'amount_currency': 100.0,   'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,       'credit': 150.0,    'amount_currency': -100.0,  'tax_ids': self.cash_basis_tax_a_third_amount.ids,  'tax_line_id': False},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 15.0,      'credit': 0.0,      'amount_currency': 10.0,    'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.tax_account_1.id,               'debit': 0.0,       'credit': 15.0,     'amount_currency': -10.0,   'tax_ids': [],                                      'tax_line_id': self.cash_basis_tax_a_third_amount.id},
        ])

        self.assertRecordValues(partial_rec.exchange_move_id.line_ids, [
            {'account_id': self.extra_receivable_account_1.id,                              'debit': 0.0,   'credit': 55.0, 'amount_currency': 0.0,     'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': caba_move.company_id.expense_currency_exchange_account_id.id,    'debit': 55.0,  'credit': 0.0,  'amount_currency': 0.0,     'tax_ids': [],                                      'tax_line_id': False},
        ])

        exchange_move = receivable_line.full_reconcile_id.exchange_move_id
        self.assertRecordValues(exchange_move.line_ids, [
            {'account_id': self.cash_basis_base_account.id,                                 'debit': 0.0,   'credit': 50.0, 'amount_currency': 0.0,     'tax_ids': self.cash_basis_tax_a_third_amount.ids,  'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,                                 'debit': 50.0,  'credit': 0.0,  'amount_currency': 0.0,     'tax_ids': [],                                      'tax_line_id': False},
            {'account_id': self.tax_account_1.id,                                           'debit': 0.0,   'credit': 5.0,  'amount_currency': 0.0,     'tax_ids': [],                                      'tax_line_id': self.cash_basis_tax_a_third_amount.id},
            {'account_id': self.cash_basis_transfer_account.id,                             'debit': 5.0,   'credit': 0.0,  'amount_currency': 0.0,     'tax_ids': [],                                      'tax_line_id': False},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -20.0,      -10.0),
        ])

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_4(self):
        ''' Test the generation of the exchange difference for a tax cash basis journal entry when the tax
        account is a reconcile one.
        '''
        currency_id = self.currency_data['currency'].id
        cash_basis_transition_account = self.env['account.account'].create({
            'code': '209.01.01',
            'name': 'Cash Basis Transition Account',
            'account_type': 'liability_current',
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

        partial_rec = cash_basis_move.line_ids.matched_credit_ids
        self.assertRecordValues(partial_rec.exchange_move_id.line_ids, [
            {'debit': 66.67,    'credit': 0.0,      'currency_id': currency_id,     'account_id': self.extra_receivable_account_1.id},
            {'debit': 0.0,      'credit': 66.67,    'currency_id': currency_id,     'account_id': self.company_data['company'].income_currency_exchange_account_id.id},
        ])

        # Exchange difference
        # 66.67 amount residual on the payment line after reconciling receivable line of the cash basis move with the payment counterpart
        # 50.00 difference of the cash_basis_move base line and the CABA entry created by the system
        self.assertRecordValues(res['full_reconcile'].exchange_move_id.line_ids, [
            {'debit': 50.0,     'credit': 0.0,      'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 50.0,     'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
        ])

    def test_reconcile_cash_basis_revert(self):
        ''' Ensure the cash basis journal entry can be reverted. '''
        self.cash_basis_transfer_account.reconcile = True
        self.cash_basis_tax_a_third_amount.cash_basis_transition_account_id = self.tax_account_1

        invoice_move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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

        payment_move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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
                Command.create({
                    'price_unit': 100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                }),
            ]
        })
        refund_move.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id = self.extra_receivable_account_1

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
        base_taxes = self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount
        base_tags = self.tax_tags[0] + self.tax_tags[4]

        # An invoice with 2 taxes:
        invoice_move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
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

        # Create a tax using the same accounts as the CABA one
        non_caba_tax = self.env['account.tax'].create({
            'name': 'tax 20%',
            'type_tax_use': 'purchase',
            'company_id': self.company_data['company'].id,
            'amount': 20,
            'tax_exigibility': 'on_invoice',
            'invoice_repartition_line_ids': [
                (0,0, {'repartition_type': 'base'}),

                (0,0, {
                    'repartition_type': 'tax',
                    'account_id': self.tax_account_1.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {'repartition_type': 'base'}),

                (0,0, {
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
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', partial_rec.ids)])

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
        # Required for `analytic_account_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        # Make the tax account reconcilable
        self.tax_account_1.reconcile = True

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
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', partial_rec.ids)])
        self.assertEqual(len(caba_move.line_ids), 4, "All lines should be there")
        self.assertEqual(caba_move.line_ids.filtered(lambda x: x.tax_line_id).balance, 66.66, "Tax amount should take into account both lines")

    def test_caba_double_tax_negative_line(self):
        """ Tests making a cash basis invoice with 2 lines using the same tax: a positive and a negative one.
        """
        invoice = self.init_invoice('in_invoice', amounts=[300, -60], post=True, taxes=self.cash_basis_tax_a_third_amount)

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 320,
            'payment_date': invoice.date,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        pmt_wizard._create_payments()

        partial_rec = invoice.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', partial_rec.ids)])

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
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', partial_rec.ids)])

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
                (0, 0, {'repartition_type': 'base'}),

                (0, 0, {'repartition_type': 'tax'}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),

                (0, 0, {'repartition_type': 'tax'}),
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
        invoice = self.env['account.move'].with_context(skip_invoice_sync=True).create({
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'move_type': 'entry',
            'line_ids': [
                # Base Tax line
                Command.create({
                    'debit': 0.0,
                    'credit': 3000.0,
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
        self.assertRecordValues(caba_move.line_ids, [
            {'balance':  3000.0, 'tax_line_id':    False},
            {'balance': -3000.0, 'tax_line_id':    False},
            {'balance':  1000.0, 'tax_line_id':    False},
            {'balance': -1000.0, 'tax_line_id': tax_a.id},
            {'balance':     1.0, 'tax_line_id':    False},
            {'balance':    -1.0, 'tax_line_id': tax_b.id},
        ])
