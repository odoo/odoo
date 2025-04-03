# -*- coding: utf-8 -*-
# pylint: disable=C0326
from contextlib import closing

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import Form, tagged, users
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
        cls.payable_account = cls.company_data['default_account_payable']
        cls.expense_account = cls.company_data['default_account_expense']
        cls.revenue_account = cls.company_data['default_account_revenue']

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
        cls.currency_data_3 = cls.setup_multi_currency_data(default_values={
            'name': 'Sand',
            'symbol': 'S',
            'currency_unit_label': 'Sand',
            'currency_subunit_label': 'Sand',
        }, rate2016=0.0001, rate2017=0.00001)

        # ==== Cash Basis Taxes setup ====

        cls.cash_basis_base_account = cls.env['account.account'].create({
            'code': 'cash.basis.base.account',
            'name': 'cash_basis_base_account',
            'account_type': 'income',
            'company_id': cls.company_data['company'].id,
        })
        cls.company_data['company'].account_cash_basis_base_account_id = cls.cash_basis_base_account

        cls.cash_basis_transfer_account = cls.env['account.account'].create({
            'code': 'cash.basis.transfer.account',
            'name': 'cash_basis_transfer_account',
            'account_type': 'income',
            'reconcile': True,
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_1 = cls.env['account.account'].create({
            'code': 'tax.account.1',
            'name': 'tax_account_1',
            'account_type': 'income',
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_2 = cls.env['account.account'].create({
            'code': 'tax.account.2',
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

    def _get_partials(self, amls):
        return (amls.matched_debit_ids | amls.matched_credit_ids).sorted()

    def _get_caba_moves(self, moves):
        return moves.search([('tax_cash_basis_origin_move_id', 'in', moves.ids)])

    @users('simple_accountman')
    def test_full_reconcile_bunch_lines(self):
        """ Test the reconciliation with multiple lines at the same time and ensure the result is always a full
        reconcile whatever the number of involved currencies.
        """
        comp_curr = self.company_data['currency']
        foreign_curr1 = self.currency_data['currency']
        foreign_curr2 = self.currency_data_2['currency']

        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, comp_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-300.0, -300.0, comp_curr, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(-400.0, -400.0, comp_curr, '2016-01-01')
        line_4 = self.create_line_for_reconciliation(-500.0, -500.0, comp_curr, '2016-01-01')
        line_5 = self.create_line_for_reconciliation(200.0, 200.0, comp_curr, '2016-01-01')
        comp_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        line_1 = self.create_line_for_reconciliation(1200.0, 3600.0, foreign_curr1, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-240.0, -480.0, foreign_curr1, '2017-01-01')
        line_3 = self.create_line_for_reconciliation(-720.0, -1440.0, foreign_curr1, '2017-01-01')
        line_4 = self.create_line_for_reconciliation(-1020.0, -2040.0, foreign_curr1, '2017-01-01')
        line_5 = self.create_line_for_reconciliation(120.0, 360.0, foreign_curr1, '2016-01-01')
        same_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        line_1 = self.create_line_for_reconciliation(1200.0, 3600.0, foreign_curr1, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(780.0, 2340.0, foreign_curr1, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(-240.0, -960.0, foreign_curr2, '2017-01-01')
        line_4 = self.create_line_for_reconciliation(-720.0, -2880.0, foreign_curr2, '2017-01-01')
        line_5 = self.create_line_for_reconciliation(-1020.0, -4080.0, foreign_curr2, '2017-01-01')
        multi_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        for batch, sub_test_name in (
                (comp_curr_batch, "Batch in company currency"),
                (same_curr_batch, "Batch in foreign currency"),
                (multi_curr_batch, "Batch with multiple currencies"),
                (comp_curr_batch + same_curr_batch + multi_curr_batch, "All batches"),
        ):
            with self.subTest(sub_test_name=sub_test_name):

                batch.reconcile()
                self.assertTrue(batch.full_reconcile_id)
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
                        line_1 = self.create_line_for_reconciliation(120.0 * rate1, 120.0, currency, '2017-01-01')
                        line_2 = self.create_line_for_reconciliation(120.0 * rate2, 120.0, currency, '2017-01-01')
                        line_3 = self.create_line_for_reconciliation(-240.0 * rate3, -240.0, currency, '2017-01-01')

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
            line1 = self.create_line_for_reconciliation(*line1_vals)
            line2 = self.create_line_for_reconciliation(*line2_vals)
            with self.subTest(line1_vals=line1_vals, line2_vals=line2_vals):
                (line1 + line2).reconcile()

                # Reconcile.
                # Don't check the result since this is already checked by another tests.
                partials = self._get_partials(line1 + line2)
                exchange_diff = partials.exchange_move_id
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

    def test_invoice_draft_fully_paid_if_zero(self):
        """ Tests that Invoices with zero balance are marked as paid and reconciled
        """
        zero_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'invoice_line_ids': [Command.create({'name': 'Nope', 'price_unit': 0})],
        })
        payment_term_line = zero_invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        self.assertRecordValues(zero_invoice, [{
            'state': 'draft',
            'payment_state': 'not_paid',
            'amount_total': 0.0,
        }])
        self.assertTrue(payment_term_line.reconciled)

        zero_invoice.action_post()
        self.assertRecordValues(zero_invoice, [{
            'state': 'posted',
            'payment_state': 'paid',
            'amount_total': 0.0,
        }])
        self.assertTrue(payment_term_line.reconciled)

    def test_reconcile_lines_corner_case_1_zero_balance_same_foreign_currency(self):
        """ Test the reconciliation of lines having a zero balance in different currencies. In that case, the reconciliation should not be full until
        an additional move is added with the right foreign currency amount. """
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(0.0, -0.02, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(0.0, 0.01, currency, '2017-01-01')
        (line_1 + line_2).reconcile()

        self.assertFalse(line_1.full_reconcile_id + line_2.full_reconcile_id, "The reconciliation should not be considered full, as 0.01 still remain open in foreign currency.")

        line_3 = self.create_line_for_reconciliation(0.0, 0.01, currency, '2017-01-01')
        (line_1 + line_3).reconcile()

        self.assertTrue(line_1.full_reconcile_id)
        self.assertEqual(line_1.full_reconcile_id, line_2.full_reconcile_id)
        self.assertEqual(line_2.full_reconcile_id, line_3.full_reconcile_id)

    def test_reconcile_lines_corner_case_1_zero_balance_different_foreign_currency(self):
        """ Test the reconciliation of lines having a zero balance in different currencies.
        In that case, we don't reconcile anything.
        """
        currency_1 = self.currency_data['currency']
        currency_2 = self.setup_multi_currency_data({
            'name': 'Bretonnian Ecu',
            'symbol': '👑',
            'currency_unit_label': 'Ecu',
            'currency_subunit_label': 'Bretonnian Denier',
        })['currency']

        line_1 = self.create_line_for_reconciliation(0.0, -0.01, currency_1, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(0.0, 0.02, currency_2, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertFalse(partials)

    def test_reconcile_lines_corner_case_2_zero_amount_currency_same_foreign_currency(self):
        """ Test a corner case when both lines have something to reconcile in company currency but nothing
        in foreign currency. It could be due to:
        - a bad usage of the `no_exchange_difference` context key
        - a partial reconciliation made before migrating to this version
        - some rounding error when dealing with currencies having != decimal places
        - strange journal items made by the user
        """
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-0.01, 0.0, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(0.02, 0.0, currency, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(partials, [
            {
                'amount': 0.01,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 0.01,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': full_reconcile.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(full_reconcile.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(full_reconcile.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
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

        line_1 = self.create_line_for_reconciliation(-0.01, -0.01, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(0.0, 0.03, foreign_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(partials, [
            {
                'amount': 0.0,
                'debit_amount_currency': 0.02,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 0.01,
                'debit_amount_currency': 0.01,
                'credit_amount_currency': 0.01,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 0.0,
                'debit_amount_currency': 0.01,
                'credit_amount_currency': 0.01,
                'debit_move_id': line_2.id,
                'credit_move_id': full_reconcile.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(full_reconcile.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(full_reconcile.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_lines_corner_case_4_zero_amount_currency_multiple_currencies(self):
        foreign_curr1 = self.currency_data['currency']
        foreign_curr2 = self.currency_data_2['currency']

        line_1 = self.create_line_for_reconciliation(-0.01, 0.0, foreign_curr2, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(0.01, 0.03, foreign_curr1, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [{
            'amount': 0.01,
            'debit_amount_currency': 0.03,
            'credit_amount_currency': 0.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
            'exchange_move_id': None,
        }])
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_lines_corner_case_5_zero_balance_in_one_line_same_foreign_currency(self):
        """ Test a corner case when both lines have something to reconcile in company currency but one has nothing
        in foreign currency. It could be due to:
        - a bad usage of the `no_exchange_difference` context key
        - a partial reconciliation made before migrating to this version
        - some rounding error when dealing with currencies having != decimal places
        - strange journal items made by the user
        """
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-0.06, 0.0, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(0.12, 0.24, currency, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 0.06,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
        ])
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.06,       'amount_residual_currency': 0.24,   'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_expense_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(60.0, 120.0, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-80.0, -240.0, currency, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_1.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -40.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_income_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(40.0, 120.0, currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-120.0, -240.0, currency, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -60.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_expense_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-40.0, -120.0, currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(120.0, 240.0, currency, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 60.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_income_partial_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -120.0, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(80.0, 240.0, currency, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 40.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(60.0, 120.0, foreign_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-80.0, -80.0, comp_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_1.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -40.0,      'amount_residual_currency': -40.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(60.0, 60.0, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-80.0, -240.0, foreign_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': line_1.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -40.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(40.0, 120.0, foreign_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-120.0, -120.0, comp_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -60.0,      'amount_residual_currency': -60.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(40.0, 40.0, comp_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-120.0, -240.0, foreign_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': -60.0,      'amount_residual_currency': -120.0, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-40.0, -120.0, foreign_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(120.0, 120.0, comp_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': line_2.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 60.0,       'amount_residual_currency': 60.0,   'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_expense_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-40.0, -40.0, comp_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(120.0, 240.0, foreign_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 60.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -60.0, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(80.0, 240.0, foreign_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 40.0,       'amount_residual_currency': 120.0,  'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_income_partial_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(80.0, 80.0, comp_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 40.0,       'amount_residual_currency': 40.0,   'reconciled': False},
        ])

    def test_reconcile_one_foreign_currency_fallback_company_currency(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data_3['currency']

        line_1 = self.create_line_for_reconciliation(-10.0, -10.0, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(1000000.0, 100.0, foreign_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(partials, [{
            'amount': 10.0,
            'debit_amount_currency': 0.001,
            'credit_amount_currency': 10.0,
            'debit_move_id': line_2.id,
            'credit_move_id': line_1.id,
        }])
        self.assertFalse(partials.exchange_move_id)
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 999990.0,   'amount_residual_currency': 99.999, 'reconciled': False},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_expense_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(60.0, 120.0, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-40.0, -120.0, currency, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_1.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_income_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(40.0, 120.0, currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-60.0, -120.0, currency, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_expense_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-40.0, -120.0, currency, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(60.0, 120.0, currency, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            }
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_income_full_payment(self):
        currency = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -120.0, currency, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(40.0, 120.0, currency, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            }
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(line_1 + line_2, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(60.0, 120.0, foreign_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-40.0, -40.0, comp_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_1.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(60.0, 60.0, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-40.0, -120.0, foreign_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': line_1.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(40.0, 120.0, foreign_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-60.0, -60.0, comp_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(40.0, 40.0, comp_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_1.id,
                'credit_move_id': line_2.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_2.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-40.0, -40.0, comp_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(60.0, 120.0, foreign_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': line_2.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_expense_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-40.0, -120.0, foreign_curr, '2016-01-01')
        line_2 = self.create_line_for_reconciliation(60.0, 60.0, comp_curr, '2017-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': line_2.id,
                'credit_move_id': partials.exchange_move_id.line_ids[0].id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -60.0, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(40.0, 120.0, foreign_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 120.0,
                'credit_amount_currency': 40.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 20.0,
                'credit_amount_currency': 20.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_income_full_payment(self):
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(40.0, 40.0, comp_curr, '2016-01-01')
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(full_reconcile, [{'exchange_move_id': False}])
        self.assertRecordValues(partials, [
            {
                'amount': 40.0,
                'debit_amount_currency': 40.0,
                'credit_amount_currency': 120.0,
                'debit_move_id': line_2.id,
                'credit_move_id': line_1.id,
            },
            {
                'amount': 20.0,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': line_1.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2017-01-31')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(amls, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,    'reconciled': True},
        ])

    def test_reconcile_invoice_company_curr_payment_foreign_curr(self):
        """ Test we always use the payment rate in priority when performing a reconciliation. """
        comp_curr = self.company_data['currency']
        foreign_curr = self.currency_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': comp_curr.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 60.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        payment = self.env['account.payment.register']\
            .with_context(active_model=invoice._name, active_ids=invoice.ids)\
            .create({
                'payment_date': '2016-01-01',
                'amount': 90.0,
                'currency_id': foreign_curr.id,
            })\
            ._create_payments()

        lines = (invoice + payment.move_id).line_ids\
            .filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        self.assertRecordValues(lines, [
            # pylint: disable=bad-whitespace
            {'amount_residual': 30.0,   'amount_residual_currency': 30.0,   'reconciled': False},
            {'amount_residual': 0.0,    'amount_residual_currency': 0.0,    'reconciled': True},
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

    def test_reconcile_foreign_currency_rounding_issue(self):
        comp_curr = self.company_data['currency']
        foreign_currency = self.env['res.currency'].create({
            'name': "Bread",
            'symbol': '🍞',
            'rounding': 0.01,
            'rate_ids': [
                Command.create({'name': '2019-06-01', 'rate': 0.052972554919}),
            ],
        })

        non_rec_pay_account = self.company_data['default_account_revenue'].copy()
        non_rec_pay_account.reconcile = True
        self.assertFalse(non_rec_pay_account.account_type in ('asset_receivable', 'liability_payable'))
        rec_pay_account = self.company_data['default_account_receivable'].copy()
        self.assertTrue(rec_pay_account.reconcile)
        self.assertTrue(rec_pay_account.account_type in ('asset_receivable', 'liability_payable'))

        # Check that the reconciliation works independently of
        # - whether the foreign amount is debit or credit
        # - the account type (payable / receivable)
        for sign, reco_account in [
            (-1, non_rec_pay_account),
            (1, non_rec_pay_account),
            (-1, rec_pay_account),
            (1, rec_pay_account),
        ]:
            with self.subTest(sub_test_name=f'sign: {sign}, reco_account: {reco_account.name}'):
                line_1 = self.create_line_for_reconciliation(
                    balance=sign * 377554.0,
                    amount_currency=sign * 20000.0,
                    currency=foreign_currency,
                    move_date='2019-06-01',
                    account_1=reco_account,
                )
                line_2 = self.create_line_for_reconciliation(
                    balance=-sign * 372239.38,
                    amount_currency=-sign * 372239.38,
                    currency=comp_curr,
                    move_date='2019-06-01',
                    account_1=reco_account,
                )
                line_3 = self.create_line_for_reconciliation(
                    balance=-sign * 5314.62,
                    amount_currency=-sign * 281.53,
                    currency=foreign_currency,
                    move_date='2019-06-01',
                    account_1=reco_account,
                )
                amls = line_1 + line_2 + line_3
                amls.reconcile()

                full_reconcile = amls.full_reconcile_id
                self.assertTrue(full_reconcile)
                self.assertTrue(all(line.full_reconcile_id == full_reconcile for line in amls))
                self.assertRecordValues(
                    amls,
                    [{'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'reconciled': True}] * len(amls),
                )

                partials = self._get_partials(amls)
                if sign == 1:
                    expected_partials = [
                        {
                            'amount': 5314.62,
                            'debit_amount_currency': 281.53,
                            'credit_amount_currency': 281.53,
                            'debit_move_id': line_1.id,
                            'credit_move_id': line_3.id,
                        },
                        {
                            'amount': 372239.38,
                            'debit_amount_currency': 19718.47,
                            'credit_amount_currency': 372239.38,
                            'debit_move_id': line_1.id,
                            'credit_move_id': line_2.id,
                        },
                    ]
                else:
                    expected_partials = [
                        {
                            'amount': 5314.62,
                            'debit_amount_currency': 281.53,
                            'credit_amount_currency': 281.53,
                            'debit_move_id': line_3.id,
                            'credit_move_id': line_1.id,
                        },
                        {
                            'amount': 372239.38,
                            'debit_amount_currency': 372239.38,
                            'credit_amount_currency': 19718.47,
                            'debit_move_id': line_2.id,
                            'credit_move_id': line_1.id,
                        },
                    ]
                self.assertRecordValues(partials.sorted('amount'), expected_partials)

    def test_reconcile_partial_exchange_rounding_issue(self):
        comp_curr = self.company_data['currency']
        foreign_currency = self.env['res.currency'].create({
            'name': "Bread",
            'symbol': '🍞',
            'rounding': 0.01,
            'rate_ids': [
                Command.create({'name': '2019-06-01', 'rate': 0.052972554919}),
            ],
        })

        non_rec_pay_account = self.company_data['default_account_revenue'].copy()
        non_rec_pay_account.reconcile = True
        self.assertFalse(non_rec_pay_account.account_type in ('asset_receivable', 'liability_payable'))
        rec_pay_account = self.company_data['default_account_receivable'].copy()
        self.assertTrue(rec_pay_account.reconcile)
        self.assertTrue(rec_pay_account.account_type in ('asset_receivable', 'liability_payable'))

        # Check that the reconciliation works independently of
        # - whether the foreign amount is debit or credit
        # - the account type (payable / receivable)
        for sign, reco_account in [
            (-1, non_rec_pay_account),
            (1, non_rec_pay_account),
            (-1, rec_pay_account),
            (1, rec_pay_account),
        ]:
            with self.subTest(sub_test_name=f'sign: {sign}, reco_account: {reco_account.name}'):
                line_1 = self.create_line_for_reconciliation(
                    balance=sign * 377554.0,
                    amount_currency=sign * 20000.0,
                    currency=foreign_currency,
                    move_date='2019-06-01',
                    account_1=reco_account,
                )
                line_2 = self.create_line_for_reconciliation(
                    balance=-sign * 372239.38,
                    amount_currency=-sign * 372239.38,
                    currency=comp_curr,
                    move_date='2019-06-01',
                    account_1=reco_account,
                )
                amls = line_1 + line_2
                amls.reconcile()

                full_reconcile = amls.full_reconcile_id
                self.assertFalse(full_reconcile)

                partials = self._get_partials(amls)
                if sign == 1:
                    expected_partials = [
                        {
                            'amount': 372239.38,
                            'debit_amount_currency': 19718.47,
                            'credit_amount_currency': 372239.38,
                            'debit_move_id': line_1.id,
                            'credit_move_id': line_2.id,
                        },
                    ]
                else:
                    expected_partials = [
                        {
                            'amount': 372239.38,
                            'debit_amount_currency': 372239.38,
                            'credit_amount_currency': 19718.47,
                            'debit_move_id': line_2.id,
                            'credit_move_id': line_1.id,
                        },
                    ]
                self.assertRecordValues(partials.sorted('amount'), expected_partials)

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

        (refund1_rec_line + inv1_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv1_rec_line)

        self.assertRecordValues(partials, [{
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

        partials = self._get_partials(refund1_rec_line + inv2_rec_line)
        (refund1_rec_line + inv2_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv2_rec_line) - partials

        self.assertRecordValues(partials, [
            {
                'amount': 540.18,
                'debit_amount_currency': 28.46,
                'credit_amount_currency': 540.18,
                'debit_move_id': inv2_rec_line.id,
                'credit_move_id': refund1_rec_line.id,
            },
            {
                'amount': 6.34,
                'debit_amount_currency': 6.34,
                'credit_amount_currency': 6.34,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': refund1_rec_line.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2019-06-30')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 36200.51,   'amount_residual_currency': 1907.26,    'reconciled': False},
        ])
        self.assert_invoice_outstanding_reconciled_widget(refund1, {
            inv1.id: 839.40,
            inv2.id: 540.18,
            partials.exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {})

        # 3th reconciliation inv1 + pay1
        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            partials.exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
        })
        self.assertRecordValues(inv2_rec_line + pay1_rec_line, [
            {'amount_residual': 36200.51,   'amount_residual_currency': 1907.26,    'reconciled': False},
            {'amount_residual': -36511.34,  'amount_residual_currency': -1907.17,   'reconciled': False},
        ])

        partials = self._get_partials(inv2_rec_line + pay1_rec_line)
        (inv2_rec_line + pay1_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay1_rec_line) - partials

        self.assertRecordValues(partials, [
            {
                'amount': 36198.80,
                'debit_amount_currency': 1907.17,
                'credit_amount_currency': 1907.17,
                'debit_move_id': inv2_rec_line.id,
                'credit_move_id': pay1_rec_line.id,
            },
            {
                'amount': 312.54,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': pay1_rec_line.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2019-06-30')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(lambda x: x not in partials)

        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            partials.exchange_move_id.id: 312.54,
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

        partials = self._get_partials(inv2_rec_line + pay2_rec_line)
        (inv2_rec_line + pay2_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay2_rec_line) - partials

        self.assertRecordValues(partials, [
            {
                'amount': 1.71,
                'debit_amount_currency': 0.09,
                'credit_amount_currency': 0.09,
                'debit_move_id': inv2_rec_line.id,
                'credit_move_id': pay2_rec_line.id,
            },
            {
                'amount': 0.06,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': pay2_rec_line.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2019-09-30')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(lambda x: x not in partials)

        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
            partials.exchange_move_id.id: 0.06,
            payment_exchange_id[0].exchange_move_id.id: 6.34,
            payment_exchange_id[1].exchange_move_id.id: 312.54,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {})

        self.assertRecordValues(inv2_rec_line.full_reconcile_id, [{'exchange_move_id': None}])

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

        (refund1_rec_line + inv1_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv1_rec_line)

        self.assertRecordValues(partials, [{
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

        (inv2_rec_line + pay1_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay1_rec_line)

        self.assertRecordValues(partials, [
            {
                'amount': 36198.8,
                'debit_amount_currency': 1907.17,
                'credit_amount_currency': 1907.17,
                'debit_move_id': inv2_rec_line.id,
                'credit_move_id': pay1_rec_line.id,
            },
            {
                'amount': 312.54,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': pay1_rec_line.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2019-06-30')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
            partials.exchange_move_id.id: 312.54,
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

        partials = self._get_partials(refund1_rec_line + inv2_rec_line)
        (refund1_rec_line + inv2_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv2_rec_line) - partials

        self.assertRecordValues(partials, [
            {
                'amount': 540.18,
                'debit_amount_currency': 28.46,
                'credit_amount_currency': 540.18,
                'debit_move_id': inv2_rec_line.id,
                'credit_move_id': refund1_rec_line.id,
            },
            {
                'amount': 6.34,
                'debit_amount_currency': 6.34,
                'credit_amount_currency': 6.34,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': refund1_rec_line.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2019-06-30')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        self.assertRecordValues(refund1_rec_line + inv2_rec_line, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 1.71,       'amount_residual_currency': 0.09,       'reconciled': False},
        ])
        self.assert_invoice_outstanding_reconciled_widget(refund1, {
            inv1.id: 839.40,
            inv2.id: 540.18,
            partials.exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {})

        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {
            pay2.move_id.id: 0.09,
        })

        partials = self._get_partials(inv2_rec_line + pay2_rec_line)
        (inv2_rec_line + pay2_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay2_rec_line) - partials

        self.assertRecordValues(partials, [
            {
                'amount': 1.71,
                'debit_amount_currency': 0.09,
                'credit_amount_currency': 0.09,
                'debit_move_id': inv2_rec_line.id,
                'credit_move_id': pay2_rec_line.id,
            },
            {
                'amount': 0.06,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
                'debit_move_id': partials.exchange_move_id.line_ids[0].id,
                'credit_move_id': pay2_rec_line.id,
            },
        ])
        self.assertRecordValues(partials.exchange_move_id, [{'date': fields.Date.from_string('2019-09-30')}])
        self.assertRecordValues(partials.exchange_move_id.line_ids, [
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
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(lambda x: x not in partials)

        self.assert_invoice_outstanding_reconciled_widget(inv2, {
            refund1.id: 28.46,
            pay1.move_id.id: 1907.17,
            pay2.move_id.id: 0.09,
            partials.exchange_move_id.id: 0.06,
            payment_exchange_id[0].exchange_move_id.id: 312.54,
            payment_exchange_id[1].exchange_move_id.id: 6.34,
        })
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {})

        self.assertRecordValues(inv2_rec_line.full_reconcile_id, [{'exchange_move_id': None}])

    def test_migration_to_new_reconciliation_same_foreign_currency(self):
        foreign_curr = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(-60.0, -120.0, foreign_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(80.0, 240.0, foreign_curr, '2016-01-01')

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
        line_3 = self.create_line_for_reconciliation(-15.0, -30.0, foreign_curr, '2017-01-01')
        (line_2 + line_3).reconcile()
        self.assertRecordValues(line_2 + line_3, [
            {'amount_residual': 10.0,       'amount_residual_currency': 90.0,       'reconciled': False},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

        line_4 = self.create_line_for_reconciliation(-30.0, -90.0, foreign_curr, '2016-01-01')
        (line_2 + line_4).reconcile()
        self.assertRecordValues(line_2 + line_4, [
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
            {'amount_residual': 0.0,        'amount_residual_currency': 0.0,        'reconciled': True},
        ])

    def test_migration_to_new_reconciliation_multiple_currencies_fix_residual_with_writeoff(self):
        comp_curr = self.company_data['currency']
        foreign_curr1 = self.currency_data['currency']

        line_1 = self.create_line_for_reconciliation(600.0, 1200.0, foreign_curr1, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-800.0, -2400.0, foreign_curr1, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(400.0, 400.0, comp_curr, '2016-01-01')

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
        line_4 = self.create_line_for_reconciliation(0.0, 600.0, foreign_curr1, '2016-01-01')
        line_5 = self.create_line_for_reconciliation(-200.0, -200.0, comp_curr, '2016-01-01')
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

    def test_reconcile_plan(self):
        comp_curr = self.company_data['currency']

        line_1 = self.create_line_for_reconciliation(600.0, 600.0, comp_curr, '2017-01-01')
        line_2 = self.create_line_for_reconciliation(-100.0, -100.0, comp_curr, '2017-01-02')
        line_3 = self.create_line_for_reconciliation(700.0, 700.0, comp_curr, '2017-01-03')
        line_5 = self.create_line_for_reconciliation(-700.0, -700.0, comp_curr, '2017-01-04')
        line_4 = self.create_line_for_reconciliation(-500.0, -500.0, comp_curr, '2017-01-05')

        with closing(self.cr.savepoint()):
            # 5 batches of 1 aml. This won't reconcile anything.
            self.env['account.move.line']._reconcile_plan([line_1, line_2, line_3, line_4, line_5])
            self.assertFalse(self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5))

        with closing(self.cr.savepoint()):
            # one batch of 5 amls.
            self.env['account.move.line']._reconcile_plan([line_1 + line_2 + line_3 + line_4 + line_5])
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {'amount': 100.0,   'debit_move_id': line_1.id, 'credit_move_id': line_2.id},
                    {'amount': 500.0,   'debit_move_id': line_1.id, 'credit_move_id': line_5.id},
                    {'amount': 200.0,   'debit_move_id': line_3.id, 'credit_move_id': line_5.id},
                    {'amount': 500.0,   'debit_move_id': line_3.id, 'credit_move_id': line_4.id},
                ],
            )

        with closing(self.cr.savepoint()):
            # Reconcile line_3 + line_5 and line_1 + line_4. line_2 is alone so will not be reconciled.
            self.env['account.move.line']._reconcile_plan([line_3 + line_5, line_1 + line_4, line_2])
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {'amount': 700.0,   'debit_move_id': line_3.id, 'credit_move_id': line_5.id},
                    {'amount': 500.0,   'debit_move_id': line_1.id, 'credit_move_id': line_4.id},
                ],
            )

        with closing(self.cr.savepoint()):
            # Reconcile line_3 + line_5 first, then line_1 + line_4, then the remaining amls with line_2.
            self.env['account.move.line']._reconcile_plan([[line_3 + line_5, line_1 + line_4, line_2]])
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {'amount': 700.0,   'debit_move_id': line_3.id, 'credit_move_id': line_5.id},
                    {'amount': 500.0,   'debit_move_id': line_1.id, 'credit_move_id': line_4.id},
                    {'amount': 100.0,   'debit_move_id': line_1.id, 'credit_move_id': line_2.id},
                ],
            )

        with closing(self.cr.savepoint()):
            # Same as the previous test but with a lot of sub-plan to test the result is the same.
            self.env['account.move.line']._reconcile_plan([[[line_3 + line_5], [[line_1 + line_4], line_2]]])
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {'amount': 700.0,   'debit_move_id': line_3.id, 'credit_move_id': line_5.id},
                    {'amount': 500.0,   'debit_move_id': line_1.id, 'credit_move_id': line_4.id},
                    {'amount': 100.0,   'debit_move_id': line_1.id, 'credit_move_id': line_2.id},
                ],
            )

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
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_1.move_id)
        receivable_lines_1.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_1.move_id) - tax_cash_basis_moves

        self.assertFullReconcile(receivable_lines_1.full_reconcile_id, receivable_lines_1)
        self.assertEqual(len(tax_cash_basis_moves), 2)
        self.assertRecordValues(tax_cash_basis_moves[0].line_ids, [
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
        self.assertRecordValues(tax_cash_basis_moves[1].line_ids, [
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
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_2.move_id)
        receivable_lines_2.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_2.move_id) - tax_cash_basis_moves

        self.assertFullReconcile(receivable_lines_2.full_reconcile_id, receivable_lines_2)
        self.assertEqual(len(tax_cash_basis_moves), 3)
        self.assertRecordValues(tax_cash_basis_moves[0].line_ids, [
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
        self.assertRecordValues(tax_cash_basis_moves[1].line_ids, [
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
        self.assertRecordValues(tax_cash_basis_moves[2].line_ids, [
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
        tax_cash_basis_moves = self._get_caba_moves(payable_lines_1.move_id)
        payable_lines_1.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(payable_lines_1.move_id) - tax_cash_basis_moves

        self.assertFullReconcile(payable_lines_1.full_reconcile_id, payable_lines_1)
        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertRecordValues(tax_cash_basis_moves.line_ids, [
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

        self.assertRecordValues(payable_lines_1.full_reconcile_id.exchange_move_id.line_ids, [
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
        receivable_lines_1.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_1.move_id)

        self.assertFullReconcileAccount(receivable_lines_1.full_reconcile_id, self.extra_receivable_account_1)
        self.assertEqual(len(tax_cash_basis_moves), 2)
        self.assertRecordValues(tax_cash_basis_moves[0].line_ids, [
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
        self.assertRecordValues(tax_cash_basis_moves[1].line_ids, [
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

        caba_transition_lines_1 = tax_cash_basis_moves.line_ids.filtered(lambda x: x.account_id == self.cash_basis_transfer_account)
        caba_transition_exchange_moves_1 = caba_transition_lines_1.matched_credit_ids.exchange_move_id
        self.assertEqual(len(caba_transition_exchange_moves_1), 2)
        self.assertRecordValues(caba_transition_exchange_moves_1[0].line_ids, [
            {'debit': 0.0,      'credit': 1.39,     'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 1.39,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.env.company.expense_currency_exchange_account_id.id},
        ])
        self.assertRecordValues(caba_transition_exchange_moves_1[1].line_ids, [
            {'debit': 0.0,      'credit': 0.48,     'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.48,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.env.company.expense_currency_exchange_account_id.id},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      -7.41,      -22.226),
            (self.tax_account_1,                    -5.57,      -11.11),
            (self.tax_account_2,                    0.0,        -0.004),
        ])

        # Reconciling all the amount in extra_receivable_account_2 should compute 3 percentages:
        # 44.45 / 133.36 = 0.333308338
        # 44.44 / 133.36 = 0.333233353
        # 0.01 / 133.36 = 0.000074985

        receivable_lines_2 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_2)
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_2.move_id)
        receivable_lines_2.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_2.move_id) - tax_cash_basis_moves

        self.assertFullReconcileAccount(receivable_lines_2.full_reconcile_id, self.extra_receivable_account_2)
        self.assertEqual(len(tax_cash_basis_moves), 3)
        self.assertRecordValues(tax_cash_basis_moves[0].line_ids, [
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
        self.assertRecordValues(tax_cash_basis_moves[1].line_ids, [
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
        self.assertRecordValues(tax_cash_basis_moves[2].line_ids, [
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

        caba_transition_lines_2 = tax_cash_basis_moves.line_ids.filtered(lambda x: x.account_id == self.cash_basis_transfer_account)
        caba_transition_exchange_moves_2 = caba_transition_lines_2.matched_credit_ids.exchange_move_id
        self.assertEqual(len(caba_transition_exchange_moves_2), 3)
        self.assertRecordValues(caba_transition_exchange_moves_2[0].line_ids, [
            {'debit': 0.01,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 0.01,     'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.env.company.income_currency_exchange_account_id.id},
        ])
        self.assertRecordValues(caba_transition_exchange_moves_2[1].line_ids, [
            {'debit': 0.0,      'credit': 1.86,     'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 1.86,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.env.company.expense_currency_exchange_account_id.id},
        ])
        self.assertRecordValues(caba_transition_exchange_moves_2[2].line_ids, [
            {'debit': 0.0,      'credit': 1.85,     'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 1.85,     'credit': 0.0,      'amount_currency': 0.0,     'currency_id': currency_id,     'account_id': self.env.company.expense_currency_exchange_account_id.id},
        ])

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        -0.002),
            (self.tax_account_1,                    -16.68,     -33.328),
            (self.tax_account_2,                    0.0,        -0.01),
        ])

        # Reconciling all the amount in extra_payable_account_1 should trigger the matching number and ensure all
        # the base amount has been covered without any rounding issue.

        payable_lines_1 = (cash_basis_move + payment_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_payable_account_1)
        tax_cash_basis_moves = self._get_caba_moves(payable_lines_1.move_id)
        payable_lines_1.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(payable_lines_1.move_id) - tax_cash_basis_moves

        self.assertFullReconcile(payable_lines_1.full_reconcile_id, payable_lines_1)
        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertRecordValues(tax_cash_basis_moves.line_ids, [
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

        self.assertRecordValues(payable_lines_1.full_reconcile_id.exchange_move_id.line_ids, [
            {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,   'credit': 0.0,      'amount_currency': -0.001,   'tax_ids': taxes.ids,   'tax_line_id': False},
            {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,   'credit': 0.0,      'amount_currency': 0.001,    'tax_ids': [],          'tax_line_id': False},
        ])

        # No exchange move should have been created when reconciling the transition account
        caba_transition_lines_3 = tax_cash_basis_moves.line_ids.filtered(lambda x: x.account_id == self.cash_basis_transfer_account)
        self.assertFalse(caba_transition_lines_3.matched_credit_ids.exchange_move_id)

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -16.68,     -33.33),
            (self.tax_account_2,                    0.0,       -0.01),
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
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertRecordValues(tax_cash_basis_moves.line_ids, [
            # Base amount:
            {'debit': 150.0,    'credit': 0.0,      'amount_currency': 300.0,   'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            {'debit': 0.0,      'credit': 150.0,    'amount_currency': -300.0,  'currency_id': currency_id,     'account_id': self.cash_basis_base_account.id},
            # tax:
            {'debit': 50.0,     'credit': 0.0,      'amount_currency': 100.0,   'currency_id': currency_id,     'account_id': self.cash_basis_transfer_account.id},
            {'debit': 0.0,      'credit': 50.0,     'amount_currency': -100.0,  'currency_id': currency_id,     'account_id': self.tax_account_1.id},
        ])

        receivable_lines2 = (payment_move + end_move).line_ids\
            .filtered(lambda line: line.account_id == self.extra_receivable_account_1)
        receivable_lines2.reconcile()

        self.assertTrue(receivable_lines2.full_reconcile_id)
        exchange_diff = receivable_lines2.full_reconcile_id.exchange_move_id
        caba_rounding_correction = exchange_diff.line_ids\
            .filtered(lambda line: line.account_id == self.cash_basis_transfer_account)\
            .sorted(lambda line: (line.account_id, line.debit, line.credit))

        self.assertFalse(caba_rounding_correction, "No cash basis rounding correction should have been created, as the difference between amounts is only due to exchange difference.")

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                  -50.0,     -100.0),
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
        self.assertFalse(exchange_move, "No exchange move difference should be created for the full reconcile object ,as there is no cash basis rounding.")

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                  -15.0,      -10.0),
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
        self.assertFalse(exchange_move, "No exchange move difference should be created for the full reconcile object ,as there is no cash basis rounding.")

        self.assertAmountsGroupByAccount([
            # Account                               Balance     Amount Currency
            (self.cash_basis_transfer_account,      0.0,        0.0),
            (self.tax_account_1,                    -15.0,      -10.0),
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
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertEqual(len(tax_cash_basis_moves), 1)

        # Tax values based on payment
        # Invoice amount 300 (amount currency) with payment rate 2 (400 payment amount divided by 200 invoice balance)
        #  - Base amount: 150 company currency
        #  - Tax amount: 50 company currency
        self.assertRecordValues(tax_cash_basis_moves.line_ids, [
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
        self.assertFalse(receivable_lines.full_reconcile_id.exchange_move_id, "No exchange move difference should be created for the full reconcile object ,as there is no cash basis rounding.")

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

        (refund + invoice).line_ids\
            .filtered(lambda x: x.account_id.account_type == 'asset_receivable')\
            .reconcile()

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
            invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable').matched_credit_ids.exchange_move_id.line_ids,
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

        self.assertFalse(invoice.line_ids.full_reconcile_id.exchange_move_id)

    def test_reconcile_cash_basis_revert(self):
        ''' Ensure the cash basis journal entry can be reverted. '''
        self.env.company.tax_exigibility = True
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
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        # == Check reconciliation of invoice with payment ==

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)
        self.assertEqual(len(tax_cash_basis_moves), 1)

        # == Check the reconciliation of invoice with tax cash basis journal entry.
        # /!\ We make the assumption the tax cash basis journal entry is well created.

        tax_cash_basis_move = tax_cash_basis_moves

        taxes_lines = (invoice_move.line_ids + tax_cash_basis_move.line_ids.filtered('debit'))\
            .filtered(lambda line: line.account_id == self.cash_basis_transfer_account)
        taxes_full_reconcile = taxes_lines.matched_debit_ids.full_reconcile_id

        self.assertTrue(taxes_full_reconcile)
        self.assertFullReconcile(taxes_full_reconcile, taxes_lines)

        # == Check the reconciliation after the reverse ==

        tax_cash_basis_move_reverse = tax_cash_basis_move._reverse_moves(cancel=True)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)

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
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)
        self.assertEqual(len(tax_cash_basis_moves), 2)

        tax_cash_basis_moves = tax_cash_basis_moves.sorted(lambda move: move.tax_cash_basis_origin_move_id.id)

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
                'journal_id': invoice.journal_id.id,
            })
        refund = self.env['account.move'].browse(reversal_wizard.refund_moves()['res_id'])
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
                'journal_id': refund.journal_id.id,
            })
        reversed_refund = self.env['account.move'].browse(reversal_wizard.refund_moves()['res_id'])

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
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)
        self.assertEqual(len(tax_cash_basis_moves), 1)

        self.assertRecordValues(tax_cash_basis_moves.line_ids, [
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

    def test_matching_number_full_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        line_b = self.create_line_for_reconciliation(-1000, -1000, currency, '2016-01-01')
        (line_a + line_b).reconcile()
        self.assertFullReconcile(line_a.full_reconcile_id, (line_a + line_b))
        self.assertEqual(line_a.matching_number, str(line_a.full_reconcile_id.id))
        self.assertEqual(line_a.matching_number, line_b.matching_number)

    def test_matching_number_partial_single_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        line_b = self.create_line_for_reconciliation(-500, -500, currency, '2016-01-01')
        (line_a + line_b).reconcile()
        self.assertEqual(line_a.matching_number, f'P{line_a.matched_credit_ids.id}')
        self.assertEqual(line_a.matching_number, line_b.matching_number)

    def test_matching_number_partial_multi_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        line_b = self.create_line_for_reconciliation(-500, -500, currency, '2016-01-01')
        line_c = self.create_line_for_reconciliation(-1000, -1000, currency, '2016-01-01')
        line_d = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        (line_a + line_b).reconcile()
        (line_a + line_c).reconcile()
        (line_c + line_d).reconcile()
        self.assertEqual(line_a.matching_number, f'P{line_a.matched_credit_ids.ids[0]}')
        self.assertEqual(line_b.matching_number, line_a.matching_number)
        self.assertEqual(line_c.matching_number, line_a.matching_number)
        self.assertEqual(line_d.matching_number, line_a.matching_number)

        line_b.remove_move_reconcile()
        self.assertEqual(line_a.matching_number, f'P{line_a.matched_credit_ids.ids[0]}')
        self.assertEqual(line_b.matching_number, False)
        self.assertEqual(line_c.matching_number, f'P{line_c.matched_debit_ids.ids[0]}')
        self.assertEqual(line_d.matching_number, line_c.matching_number)

        (line_a + line_b).reconcile()  # everything should be matched again
        self.assertEqual(line_a.matching_number, line_c.matching_number)
        self.assertEqual(line_b.matching_number, line_c.matching_number)
        self.assertEqual(line_c.matching_number, f'P{line_c.matched_debit_ids.ids[0]}')
        self.assertEqual(line_d.matching_number, line_c.matching_number)

    def test_matching_number_partial_multi_separate_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        line_b = self.create_line_for_reconciliation(-500, -500, currency, '2016-01-01')
        (line_a + line_b).reconcile()
        self.assertEqual(line_a.matching_number, f'P{line_a.matched_credit_ids.id}')
        self.assertEqual(line_a.matching_number, line_b.matching_number)

        line_c = self.create_line_for_reconciliation(-300, -300, currency, '2016-01-01')
        (line_a + line_c).reconcile()
        self.assertEqual(line_a.matching_number, f'P{line_a.matched_credit_ids.ids[0]}')
        self.assertEqual(line_a.matching_number, line_b.matching_number)
        self.assertEqual(line_a.matching_number, line_c.matching_number)

    def test_matching_number_unreconcile_single(self):
        currency = self.env.company.currency_id
        full_line_a = self.create_line_for_reconciliation(200, 200, currency, '2016-01-01')
        full_line_b = self.create_line_for_reconciliation(-200, -200, currency, '2016-01-01')
        partial_line_a = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        partial_line_b = self.create_line_for_reconciliation(-500, -500, currency, '2016-01-01')
        (full_line_a + full_line_b).reconcile()
        (partial_line_a + partial_line_b).reconcile()
        (full_line_a + full_line_b + partial_line_a + partial_line_b).remove_move_reconcile()
        self.assertFalse(full_line_a.matching_number)
        self.assertFalse(full_line_b.matching_number)
        self.assertFalse(partial_line_a.matching_number)
        self.assertFalse(partial_line_b.matching_number)

    def test_matching_number_unreconcile_multi(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(-500, -500, currency, '2016-01-01')
        line_b = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        line_c = self.create_line_for_reconciliation(-1000, -1000, currency, '2016-01-01')
        line_d = self.create_line_for_reconciliation(300, 300, currency, '2016-01-01')
        (line_a + line_b).reconcile()
        (line_b + line_c).reconcile()
        (line_c + line_d).reconcile()

        previous_matching_number = line_a.matching_number
        line_a.remove_move_reconcile()
        self.assertFalse(line_a.matching_number)
        self.assertNotEqual(previous_matching_number, line_b.matching_number)
        self.assertEqual(line_b.matching_number, line_c.matching_number)
        self.assertEqual(line_b.matching_number, line_d.matching_number)

        previous_matching_number = line_b.matching_number
        line_b.remove_move_reconcile()
        self.assertFalse(line_b.matching_number)
        self.assertNotEqual(previous_matching_number, line_c.matching_number)
        self.assertEqual(line_c.matching_number, line_d.matching_number)

        line_c.remove_move_reconcile()
        self.assertFalse(line_c.matching_number)
        self.assertFalse(line_d.matching_number)

    def test_matching_loop(self):
        currency = self.env.company.currency_id
        wrong_credit = self.create_line_for_reconciliation(-500, -500, currency, '2016-01-01')
        debit_a = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        credit_a = self.create_line_for_reconciliation(-1000, -1000, currency, '2016-01-01')
        debit_b = self.create_line_for_reconciliation(1000, 1000, currency, '2016-01-01')
        credit_b = self.create_line_for_reconciliation(-1000, -1000, currency, '2016-01-01')
        (wrong_credit + debit_a).reconcile()
        (debit_a + credit_a).reconcile()
        wrong_credit.remove_move_reconcile()  # now there is an open amount on both the payment and the invoice
        (credit_a + debit_b).reconcile()
        (debit_b + credit_b).reconcile()
        # Everything is reconciled but some amounts are still open
        self.assertEqual(len(set((debit_a + debit_b + credit_a + credit_b).mapped('matching_number'))), 1)
        self.assertFalse(all(aml.amount_residual == 0 for aml in (debit_a, debit_b, credit_a, credit_b)))

        # Now this should create a loop, it should still work, and the residual amounts should now reach 0
        (credit_b + debit_a).reconcile()
        self.assertTrue(all(aml.amount_residual == 0 for aml in (debit_a, debit_b, credit_a, credit_b)))

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

        self.env['account.tax.group'].create({
            'name': 'tax_group',
            'country_id': test_country.id,
        })

        foreign_caba_tax = self.env['account.tax'].create({
            'name': 'foreign tax_1',
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

        self.assertEqual(caba_move.fiscal_position_id, foreign_vat_fpos, "The foreign VAT fiscal position should be kept in the cash basis move.")

    def test_caba_tax_group(self):
        """ Test the CABA entries generated from an invoice with
        a tax group
        """
        self.env.company.tax_exigibility = True

        # Make the tax account reconcilable
        self.tax_account_1.reconcile = True

        # Create an invoice with a CABA tax using 'Include in analytic cost'
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
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
        exchange_difference_move = invoice.line_ids.filtered(lambda line: line.account_id.account_type == 'receivable').full_reconcile_id.exchange_move_id
        self.assertFalse(exchange_difference_move)

    def test_caba_rounding_adjustment_monocurrency(self):
        self.env.company.tax_exigibility = True

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'invoice_line_ids': [Command.create({
                'name': 'caba test',
                'quantity': 1,
                'price_unit': 99.99,
                'tax_ids': [Command.set(self.cash_basis_tax_a_third_amount.ids)],
            })],
        })
        invoice.action_post()

        payment_date_1 = fields.Date.from_string('2017-01-01')
        payment_date_2 = fields.Date.from_string('2018-01-01')

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 66.66,
            'payment_date': payment_date_1,
        })
        pmt_wizard._create_payments()

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 66.66,
            'payment_date': payment_date_2,
        })
        pmt_wizard._create_payments()

        self.assertRecordValues(invoice.tax_cash_basis_created_move_ids.filtered(lambda x: x.date == payment_date_1).line_ids, [
            # pylint: disable=bad-whitespace
            {'account_id': self.cash_basis_base_account.id,     'debit': 50.0,  'credit':  0.0},
            {'account_id': self.cash_basis_base_account.id,     'debit':  0.0,  'credit': 50.0},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 16.67, 'credit':  0.0},
            {'account_id': self.tax_account_1.id,               'debit':  0.0,  'credit': 16.67},
        ])

        self.assertRecordValues(invoice.tax_cash_basis_created_move_ids.filtered(lambda x: x.date == payment_date_2).line_ids, [
            # pylint: disable=bad-whitespace
            {'account_id': self.cash_basis_base_account.id,     'debit': 50.0,  'credit':  0.0},
            {'account_id': self.cash_basis_base_account.id,     'debit':  0.0,  'credit': 50.0},
            {'account_id': self.cash_basis_transfer_account.id, 'debit': 16.67, 'credit':  0.0},
            {'account_id': self.tax_account_1.id,               'debit':  0.0,  'credit': 16.67},
        ])

        # Check the CABA adjustment made in the receivable account's full reconcile's exchange move
        self.assertRecordValues(
            # pylint: disable=bad-whitespace
            invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable').full_reconcile_id.exchange_move_id.line_ids,
            [
                {'account_id': self.cash_basis_base_account.id,     'debit': 0.01,  'credit': 0.0},
                {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,   'credit': 0.01},
                {'account_id': self.tax_account_1.id,               'debit': 0.01,  'credit': 0.0},
                {'account_id': self.cash_basis_transfer_account.id, 'debit': 0.0,   'credit': 0.01},
            ]
        )

        self.assertEqual(
            invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable').full_reconcile_id.exchange_move_id.journal_id.id,
            self.env.company.tax_cash_basis_journal_id.id,
        )

        self.assertTrue(
            invoice.line_ids.filtered(lambda x: x.account_id == self.cash_basis_transfer_account).full_reconcile_id,
            "The cash basis transition account line of the invoice should be fully reconciled with the CABA moves and the adjustment."
        )

        self.assertAmountsGroupByAccount([
            # pylint: disable=bad-whitespace
            # Account                               Balance  Amount Currency
            (self.cash_basis_transfer_account,        0.0,     0.0),
            (self.tax_account_1,                    -33.33,  -33.33),
            (self.cash_basis_base_account,            0.0,     0.0)
        ])

    def test_caba_rounding_adjustment_multicurrency(self):
        self.env.company.tax_exigibility = True

        # Rates are 1/3 for 2016, 1/2 for 2017 and 5/1 in 2018
        currency_id = self.setup_multi_currency_data({'name': 'Minovsky Dollar', 'rounding': 0.01})['currency'].id

        self.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 0.2,
            'currency_id': currency_id,
            'company_id': self.env.company.id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'currency_id': currency_id,
            'invoice_line_ids': [Command.create({
                'name': 'caba test',
                'quantity': 1,
                'price_unit': 99.99,
                'tax_ids': [Command.set(self.cash_basis_tax_a_third_amount.ids)],
            })],
        })
        invoice.action_post()

        payment_date_1 = fields.Date.from_string('2017-01-01')
        payment_date_2 = fields.Date.from_string('2018-01-01')

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 66.66,
            'currency_id': currency_id,
            'payment_date': payment_date_1,
        })
        pmt_wizard._create_payments()

        pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': 66.66,
            'currency_id': currency_id,
            'payment_date': payment_date_2,
        })
        pmt_wizard._create_payments()

        self.assertRecordValues(invoice.tax_cash_basis_created_move_ids.filtered(lambda x: x.date == payment_date_1).line_ids, [
            # pylint: disable=bad-whitespace
            {'account_id': self.cash_basis_base_account.id,     'debit': 25.0,  'credit':  0.0,  'amount_currency':  50.0,  'currency_id': currency_id},
            {'account_id': self.cash_basis_base_account.id,     'debit':  0.0,  'credit': 25.0,  'amount_currency': -50.0,  'currency_id': currency_id},
            {'account_id': self.cash_basis_transfer_account.id, 'debit':  8.34, 'credit':  0.0,  'amount_currency':  16.67, 'currency_id': currency_id},
            {'account_id': self.tax_account_1.id,               'debit':  0.0,  'credit':  8.34, 'amount_currency': -16.67, 'currency_id': currency_id},
        ])

        self.assertRecordValues(invoice.tax_cash_basis_created_move_ids.filtered(lambda x: x.date == payment_date_2).line_ids, [
            # pylint: disable=bad-whitespace
            {'account_id': self.cash_basis_base_account.id,     'debit': 250.0,  'credit':   0.0,  'amount_currency':  50.0,  'currency_id': currency_id},
            {'account_id': self.cash_basis_base_account.id,     'debit':   0.0,  'credit': 250.0,  'amount_currency': -50.0,  'currency_id': currency_id},
            {'account_id': self.cash_basis_transfer_account.id, 'debit':  83.35, 'credit':   0.0,  'amount_currency':  16.67, 'currency_id': currency_id},
            {'account_id': self.tax_account_1.id,               'debit':   0.0,  'credit':  83.35, 'amount_currency': -16.67, 'currency_id': currency_id},
        ])

        # Check the CABA adjustment made in the receivable account's full reconcile's exchange move
        self.assertRecordValues(
            # pylint: disable=bad-whitespace
            invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable').full_reconcile_id.exchange_move_id.line_ids,
            [
                {'account_id': self.cash_basis_base_account.id,     'debit': 0.05,  'credit': 0.0,  'amount_currency':  0.01, 'currency_id': currency_id},
                {'account_id': self.cash_basis_base_account.id,     'debit': 0.0,   'credit': 0.05, 'amount_currency': -0.01, 'currency_id': currency_id},
                {'account_id': self.tax_account_1.id,               'debit': 0.05,  'credit': 0.0,  'amount_currency':  0.01, 'currency_id': currency_id},
                {'account_id': self.cash_basis_transfer_account.id, 'debit': 0.0,   'credit': 0.05, 'amount_currency': -0.01, 'currency_id': currency_id},
            ]
        )

        self.assertTrue(
            invoice.line_ids.filtered(lambda x: x.account_id == self.cash_basis_transfer_account).full_reconcile_id,
            "The cash basis transition account line of the invoice should be fully reconciled with the CABA moves and the adjustment."
        )

        self.assertAmountsGroupByAccount([
            # pylint: disable=bad-whitespace
            # Account                               Balance  Amount Currency
            (self.cash_basis_transfer_account,        0.0,     0.0),
            (self.tax_account_1,                    -91.64,  -33.33),
            (self.cash_basis_base_account,            0.0,     0.0),
        ])

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
                'reason': 'test_cash_basis_full_refund',
                'journal_id': invoice.journal_id.id,
            })
        action_values = credit_note_wizard.modify_moves()
        self.assertRecordValues(invoice, [{'payment_state': 'reversed'}])

        # Check no CABA move has been created.
        cash_basis_moves = self.env['account.move']\
            .search([('tax_cash_basis_origin_move_id', 'in', (invoice.id, action_values['res_id']))])
        self.assertFalse(cash_basis_moves)

        # No exchange journal entry created for CABA.
        caba_transfer_amls = self.env['account.move.line'].search([
            ('account_id', '=', self.cash_basis_transfer_account.id),
            ('move_id.move_type', '=', 'entry'),
        ])
        self.assertFalse(caba_transfer_amls.move_id)

    def test_reconcile_import(self):
        """Test that the import of matchings does a real matching upon posting"""
        comp_curr = self.company_data['currency']

        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, comp_curr, '2016-01-01')
        line_1.move_id.button_draft()
        line_2 = self.create_line_for_reconciliation(-300.0, -300.0, comp_curr, '2016-01-01')
        line_3 = self.create_line_for_reconciliation(-400.0, -400.0, comp_curr, '2016-01-01')
        line_4 = self.create_line_for_reconciliation(-500.0, -500.0, comp_curr, '2016-01-01')
        line_4.move_id.button_draft()
        line_5 = self.create_line_for_reconciliation(200.0, 200.0, comp_curr, '2016-01-01')
        (line_1 + line_2 + line_3).matching_number = '11111'  # Will be converted to a temporary number
        (line_4 + line_5).matching_number = '22222'  # Will be converted to a temporary number
        # posting triggers the matching of the imported values
        (line_1 + line_4).move_id.action_post()
        self.assertRegex(line_1.matching_number, r'^P\d+')
        self.assertRegex(line_4.matching_number, r'^P\d+')
        (line_1 + line_4).reconcile()
        self.assertRegex(line_1.matching_number, r'^\d+')
        self.assertTrue(line_1.full_reconcile_id)

    def test_reconcile_payment_custom_rate(self):
        """When reconciling a payment we want to take the accounting rate and not the odoo rate.
        Most likely the payment information are derived from information of the bank, therefore have
        the relevant rate.
        """
        company_currency = self.company_data['currency']
        foreign_currency = self.currency_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': company_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 400.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        payment = self.env['account.payment'].create({
            'date': invoice.date,
            'amount': 800.0,
            'currency_id': foreign_currency.id,
            'partner_id': self.partner_a.id,
        })
        payment.action_post()
        # unlink the rate to simulate a custom rate on the payment
        self.env['res.currency.rate'].search([('currency_id', '=', foreign_currency.id)]).unlink()

        lines_to_reconcile = (invoice + payment.move_id).line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        lines_to_reconcile.reconcile()

        self.assertTrue(all(lines_to_reconcile.mapped('reconciled')), "All lines should be fully reconciled")

    def test_reconcile_payment_with_no_exchange_diff_journal(self):
        """
        Test that the currency exchange journal is only required when creating exchange difference entries.
        """

        # Make sure the currency exchange journal is unset.
        self.env.company.currency_exchange_journal_id = False

        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [
                Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []}),
            ],
        }

        payment_vals = {
            'currency_id': self.currency_data['currency'].id,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.env.company.expense_currency_exchange_account_id.id,
        }

        # Check that a payment can be created if no exchange difference entry is generated.
        invoice_no_diff = self.env['account.move'].create(
            {**move_vals, 'date': '2017-01-01', 'invoice_date': '2017-01-01'}
        )
        invoice_no_diff.action_post()
        wizard_no_diff = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice_no_diff.ids)\
            .create({**payment_vals, 'payment_date': '2017-01-01', 'amount': 3000})  # 3000 GOL = 1000 USD.
        wizard_no_diff._create_payments()

        # Then check that an error is raised when trying to create a payment with an exchange difference.
        invoice_diff = self.env['account.move'].create(
            {**move_vals, 'date': '2016-01-01', 'invoice_date': '2016-01-01'}
        )
        invoice_diff.action_post()
        wizard_diff = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice_diff.ids)\
            .create({**payment_vals, 'payment_date': '2018-01-01', 'amount': 2000})  # 2000 GOL = 1000 USD.
        with self.assertRaises(UserError):
            wizard_diff._create_payments()

    def test_cash_basis_with_analytic_distribution(self):
        """
        Check that the analytic distribution is applied correctly to the cash basis move lines.
        The tax used here is not an analytic tax (field `analytic` on the tax is `False`).
        """
        self.env.company.tax_exigibility = True

        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Default',
        })
        analytic_account_a = self.env['account.analytic.account'].create({
            'name': 'analytic_account_a',
            'plan_id': analytic_plan.id,
            'company_id': False,
        })
        analytic_account_b = self.env['account.analytic.account'].create({
            'name': 'analytic_account_b',
            'plan_id': analytic_plan.id,
            'company_id': False,
        })
        analytic_distribution_a = {
            analytic_account_a.id: 100,
        }
        analytic_distribution_b = {
            analytic_account_b.id: 100,
        }
        analytic_distribution_a_serialized = {
            str(analytic_account_a.id): 100,
        }
        analytic_distribution_b_serialized = {
            str(analytic_account_b.id): 100,
        }

        tax = self.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'analytic': False,
            'cash_basis_transition_account_id': self.cash_basis_transfer_account.id,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 30,
                    'account_id': self.tax_account_1.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True,
                }),
                Command.create({
                    'factor_percent': 70,
                    'account_id': self.tax_account_2.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 30,
                    'account_id': self.tax_account_1.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True,
                }),
                Command.create({
                    'factor_percent': 70,
                    'account_id': self.tax_account_2.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False,
                }),
            ],
        })

        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                    'analytic_distribution': analytic_distribution_a,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                    'analytic_distribution': analytic_distribution_b,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                    'analytic_distribution': analytic_distribution_b,
                }),
            ]
        }])
        invoice.action_post()

        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()

        # Check the caba move lines.
        # I.e. lines with different analytic distributions should not be grouped / mixed together.
        # The value of the `use_in_tax_closing` field on the repartition lines is important.
        # (Here) It determines whether the analytic distribution will be applied to the journal items or not.
        # When creating the caba move (lines) only the journal items (and their analytic distribution) are considered
        # (and not the invoice lines).
        #   * base repartition lines: use_in_tax_closing is False (default computed); the analytic distribution will be applied.
        #     They should be separated by analytic distribution.
        #   * 30% repartition line: use_in_tax_closing is True; the analytic distribution will not be applied.
        #     They should all be grouped together.
        #   * 70% repartiton line: use_in_tax_closing is False; the analytic distribution will be applied.
        #     They should be separated by analytic distribution.
        caba_move = invoice.tax_cash_basis_created_move_ids
        expected_caba_move_line_values = [
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 0.0,
                'credit': 100.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 100.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 0.0,
                'credit': 200.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 200.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.tax_account_1.id,
                'debit': 0.0,
                'credit': 18.0,
                'analytic_distribution': False,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 18.0,
                'credit': 0.0,
                'analytic_distribution': False,
            },
            {
                'account_id': self.tax_account_2.id,
                'debit': 0.0,
                'credit': 14.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 14.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.tax_account_2.id,
                'debit': 0.0,
                'credit': 28.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 28.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
        ]
        self.assertRecordValues(caba_move.line_ids.sorted('id').sorted('sequence'), expected_caba_move_line_values)

    def test_cash_basis_with_analytic_distribution_analytic_tax(self):
        """
        Check that the analytic distribution is applied correctly to the cash basis move lines.
        The tax used here is not an analytic tax (field `analytic` on the tax is `True`).
        """
        self.env.company.tax_exigibility = True

        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Default',
        })
        analytic_account_a = self.env['account.analytic.account'].create({
            'name': 'analytic_account_a',
            'plan_id': analytic_plan.id,
            'company_id': False,
        })
        analytic_account_b = self.env['account.analytic.account'].create({
            'name': 'analytic_account_b',
            'plan_id': analytic_plan.id,
            'company_id': False,
        })
        analytic_distribution_a = {
            analytic_account_a.id: 100,
        }
        analytic_distribution_b = {
            analytic_account_b.id: 100,
        }
        analytic_distribution_a_serialized = {
            str(analytic_account_a.id): 100,
        }
        analytic_distribution_b_serialized = {
            str(analytic_account_b.id): 100,
        }

        tax = self.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'analytic': True,
            'cash_basis_transition_account_id': self.cash_basis_transfer_account.id,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 30,
                    'account_id': self.tax_account_1.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True,
                }),
                Command.create({
                    'factor_percent': 70,
                    'account_id': self.tax_account_2.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 30,
                    'account_id': self.tax_account_1.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True,
                }),
                Command.create({
                    'factor_percent': 70,
                    'account_id': self.tax_account_2.id,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False,
                }),
            ],
        })

        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                    'analytic_distribution': analytic_distribution_a,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                    'analytic_distribution': analytic_distribution_b,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                    'analytic_distribution': analytic_distribution_b,
                }),
            ]
        }])
        invoice.action_post()

        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()

        # Check the caba move lines.
        # I.e. lines with different analytic distributions should not be grouped / mixed together.
        # The value of the `analytic` field on the tax is `True` here.
        # Thus the analytic distribution will be applied to all the journal items
        # (i.e. even though `use_in_tax_closing` is `True` on the 30% repartition line).
        # When creating the caba move (lines) only the journal items (and their analytic distribution) are considered
        # (and not the invoice lines).
        # Thus on the caba move the base / 30% and 70% repartition lines are all separated by the analytic distribution respectively.
        caba_move = invoice.tax_cash_basis_created_move_ids
        expected_caba_move_line_values = [
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 0.0,
                'credit': 100.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 100.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 0.0,
                'credit': 200.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.cash_basis_base_account.id,
                'debit': 200.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.tax_account_1.id,
                'debit': 0.0,
                'credit': 6.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 6.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.tax_account_2.id,
                'debit': 0.0,
                'credit': 14.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 14.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_a_serialized,
            },
            {
                'account_id': self.tax_account_1.id,
                'debit': 0.0,
                'credit': 12.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 12.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.tax_account_2.id,
                'debit': 0.0,
                'credit': 28.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
            {
                'account_id': self.cash_basis_transfer_account.id,
                'debit': 28.0,
                'credit': 0.0,
                'analytic_distribution': analytic_distribution_b_serialized,
            },
        ]
        self.assertRecordValues(caba_move.line_ids.sorted('id').sorted('sequence'), expected_caba_move_line_values)
