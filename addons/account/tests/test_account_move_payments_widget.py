# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import new_test_user, tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountMovePaymentsWidget(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.payable_account = cls.company_data['default_account_payable']

        cls.curr_1 = cls.company_data['currency']
        cls.curr_2 = cls.setup_other_currency('EUR')
        cls.curr_3 = cls.setup_other_currency('CAD', rates=[('2016-01-01', 6.0), ('2017-01-01', 4.0)])

        cls.payment_2016_curr_1 = cls.env['account.move'].create({
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -500.0,  'currency_id': cls.curr_1.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 500.0,   'currency_id': cls.curr_1.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2016_curr_1.action_post()

        cls.payment_2016_curr_2 = cls.env['account.move'].create({
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -1550.0, 'currency_id': cls.curr_2.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 1550.0,  'currency_id': cls.curr_2.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2016_curr_2.action_post()

        cls.payment_2017_curr_2 = cls.env['account.move'].create({
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -950.0, 'currency_id': cls.curr_2.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 950.0,  'currency_id': cls.curr_2.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2017_curr_2.action_post()

        cls.payment_2016_curr_3 = cls.env['account.move'].create({
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -3050.0, 'currency_id': cls.curr_3.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 3050.0,  'currency_id': cls.curr_3.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2016_curr_3.action_post()

        cls.payment_2017_curr_3 = cls.env['account.move'].create({
            'date': '2017-01-01',
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 500.0,    'amount_currency': -1950.0, 'currency_id': cls.curr_3.id,   'account_id': cls.receivable_account.id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 500.0,     'credit': 0.0,      'amount_currency': 1950.0,  'currency_id': cls.curr_3.id,   'account_id': cls.payable_account.id,       'partner_id': cls.partner_a.id}),
            ],
        })
        cls.payment_2017_curr_3.action_post()

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    def test_outstanding_payments_single_currency(self):
        ''' Test the outstanding payments widget on invoices having the same currency
        as the company one.
        '''

        # Customer invoice of 2500.0 in curr_1.
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        })
        out_invoice.action_post()

        # Vendor bill of 2500.0 in curr_1.
        in_invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        })
        in_invoice.action_post()

        expected_amounts = {
            self.payment_2016_curr_1.id: 500.0,
            self.payment_2016_curr_2.id: 500.0,
            self.payment_2017_curr_2.id: 500.0,
            self.payment_2016_curr_3.id: 500.0,
            self.payment_2017_curr_3.id: 500.0,
        }

        self.assert_invoice_outstanding_to_reconcile_widget(out_invoice, expected_amounts)
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoice, expected_amounts)

    def test_outstanding_payments_foreign_currency(self):
        ''' Test the outstanding payments widget on invoices having a foreign currency. '''

        # Customer invoice of 2500.0 in curr_1.
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 7500.0})],
        })
        out_invoice.action_post()

        # Vendor bill of 2500.0 in curr_1.
        in_invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 7500.0})],
        })
        in_invoice.action_post()

        expected_amounts = {
            self.payment_2016_curr_1.id: 1500.0,
            self.payment_2016_curr_2.id: 1550.0,
            self.payment_2017_curr_2.id: 950.0,
            self.payment_2016_curr_3.id: 1500.0,
            self.payment_2017_curr_3.id: 1000.0,
        }

        self.assert_invoice_outstanding_to_reconcile_widget(out_invoice, expected_amounts)
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoice, expected_amounts)

    def test_payments_with_exchange_difference_payment(self):
        ''' Test the payments widget on invoices having a foreign currency that triggers an exchange difference on the payment. '''

        # Customer invoice of 300 in GOL at exchage rate 3:1. 300 GOL -> 100 USD
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300,
                'tax_ids': [],
            })],
        })
        out_invoice.action_post()

        # Payment at exchange rate 2:1. 300 GOL -> 150 USD
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=out_invoice.ids)\
            .create({'payment_date': '2017-01-01'})\
            ._create_payments()

        expected_amounts = {payment.move_id.id: 300.0}
        # Get the exchange difference move.
        for ln in out_invoice.line_ids:
            if ln.matched_credit_ids.exchange_move_id:
                expected_amounts[ln.matched_credit_ids.exchange_move_id.id] = 50.0

        self.assert_invoice_outstanding_reconciled_widget(out_invoice, expected_amounts)

    def test_payments_with_exchange_difference_invoice(self):
        ''' Test the payments widget on invoices having a foreign currency that triggers an exchange difference on the invoice. '''

        # Customer invoice of 300 in GOL at exchage rate 2:1. 300 GOL -> 150 USD
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_2.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300,
                'tax_ids': [],
            })],
        })
        out_invoice.action_post()

        # Payment at exchange rate 3:1. 300 GOL -> 100 USD
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=out_invoice.ids)\
            .create({'payment_date': '2016-01-01'})\
            ._create_payments()

        expected_amounts = {payment.move_id.id: 300.0}
        # Get the exchange difference move.
        for ln in out_invoice.line_ids:
            if ln.matched_credit_ids.exchange_move_id:
                expected_amounts[ln.matched_credit_ids.exchange_move_id.id] = 50.0

        self.assert_invoice_outstanding_reconciled_widget(out_invoice, expected_amounts)

    def test_outstanding_payments_branch_and_companies(self):
        """ Test the outstanding payments widget on invoices of a branch
        of the company having oustanding payments.
        """

        branch_a, branch_b = self.env['res.company'].create([{
            'name': name,
            'parent_id': self.env.company.id,
        } for name in ['Branch A', 'Branch B']])
        self.cr.precommit.run()  # load the CoA

        other_company_data = self.setup_other_company()
        other_company = other_company_data['company']

        self.env['account.journal'].with_company(company=other_company).create([
            {'name': 'sale', 'type': 'sale', 'code': 'SALE'},
            {'name': 'purchase', 'type': 'purchase', 'code': 'BUY'},
        ])

        # Customer invoice of 2500.0 in curr_1.
        out_invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'company_id': company.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        } for company in [branch_a, branch_b, other_company, self.company]])
        out_invoices.action_post()

        # Vendor bill of 2500.0 in curr_1.
        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.curr_1.id,
            'company_id': company.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': 2500.0})],
        } for company in [branch_a, branch_b, other_company, self.company]])
        in_invoices.action_post()

        out_refund = self.env['account.move'].create([{
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'company_id': branch.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': price})],
        } for branch, price in zip((branch_a, branch_b), (2500.0, 1000.0))])
        out_refund.action_post()
        in_refund = self.env['account.move'].create([{
            'move_type': 'in_refund',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch.id,
            'invoice_line_ids': [(0, 0, {'name': '/', 'price_unit': price})],
        } for branch, price in zip((branch_a, branch_b), (2500.0, 1000.0))])
        in_refund.action_post()

        expected_amounts = {
            self.payment_2016_curr_1.id: 500.0,
            self.payment_2016_curr_2.id: 500.0,
            self.payment_2017_curr_2.id: 500.0,
            self.payment_2016_curr_3.id: 500.0,
            self.payment_2017_curr_3.id: 500.0,
        }

        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[0], {out_refund[0].id: 2500.0})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[0], {in_refund[0].id: 2500.0})
        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[1], {out_refund[1].id: 1000.0})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[1], {in_refund[1].id: 1000.0})
        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[2], {})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[2], {})
        self.assert_invoice_outstanding_to_reconcile_widget(out_invoices[3], {**expected_amounts, out_refund[0].id: 2500.0, out_refund[1].id: 1000.0})
        self.assert_invoice_outstanding_to_reconcile_widget(in_invoices[3], {**expected_amounts, in_refund[0].id: 2500.0, in_refund[1].id: 1000.0})

    def test_payments_widget_open_moves_access(self):
        """ Invoicing users can open the payments and invoices from the payments widget, but not the bank transactions
        and journal entries.
        """
        invoicing_user = new_test_user(self.env, login='invoicing_user', groups='base.group_user,account.group_account_invoice')
        accountant = new_test_user(self.env, login='accountant', groups='base.group_user,account.group_account_readonly')

        out_invoice = self.init_invoice('out_invoice', amounts=[3000.0], post=True)
        payment = self.init_payment(100.0, post=True)
        out_refund = self.init_invoice('out_refund', amounts=[100.0], post=True)
        statement_line_move = self.pay_with_statement_line(
            out_invoice, self.company_data['default_journal_bank'].id, '2019-01-01', 100.0,
        )['statement_line_reconciled'].move_id

        def get_can_open_moves(user, widget_field):
            out_invoice.invalidate_recordset([widget_field])
            return {vals['move_id']: vals['can_open_move'] for vals in out_invoice.with_user(user)[widget_field]['content']}

        self.assertDictEqual(get_can_open_moves(invoicing_user, 'invoice_outstanding_credits_debits_widget'), {
            payment.move_id.id: True,
            out_refund.id: True,
            self.payment_2016_curr_1.id: False,
            self.payment_2016_curr_2.id: False,
            self.payment_2017_curr_2.id: False,
            self.payment_2016_curr_3.id: False,
            self.payment_2017_curr_3.id: False,
        })
        self.assertDictEqual(get_can_open_moves(invoicing_user, 'invoice_payments_widget'), {statement_line_move.id: False})

        self.assertTrue(all(get_can_open_moves(accountant, 'invoice_outstanding_credits_debits_widget').values()))
        self.assertDictEqual(get_can_open_moves(accountant, 'invoice_payments_widget'), {statement_line_move.id: True})
