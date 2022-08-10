# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command

from collections import defaultdict
from unicodedata import normalize

@tagged('post_install', '-at_install')
class TestAccountMovePaymentsWidget(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.payable_account = cls.company_data['default_account_payable']

        cls.currency_data_2 = cls.setup_multi_currency_data(default_values={
            'name': 'Stars',
            'symbol': '☆',
            'currency_unit_label': 'Stars',
            'currency_subunit_label': 'Little Stars',
        }, rate2016=6.0, rate2017=4.0)

        cls.curr_1 = cls.company_data['currency']
        cls.curr_2 = cls.currency_data['currency']
        cls.curr_3 = cls.currency_data_2['currency']

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

    def assert_compare_invoice_widgets(self, invoice, expected_amounts):
        ''' Compare the outstanding and reconciled amounts of the invoice with the expected amounts.
        In case outstanding amounts contain same move_ids'''
        invoice.invalidate_recordset(['invoice_payments_widget'])
        widget_vals = invoice.invoice_payments_widget
        current_amounts = defaultdict(lambda: defaultdict(list))

        if widget_vals:
            for vals in widget_vals['content']:
                current_amounts[vals['move_id']]['amount'].append(vals['amount'])
                current_amounts[vals['move_id']]['amount_company_currency'] = normalize(
                    'NFKD', vals['amount_company_currency'])
                if vals['amount_foreign_currency']:
                    current_amounts[vals['move_id']]['amount_foreign_currency'] = normalize(
                        'NFKD', vals['amount_foreign_currency'])
        else:
            current_amounts = {}
        self.assertDictEqual(current_amounts, expected_amounts)

    def _create_invoice(self, amount, partner_id, invoice_type, num_invoices=1, currency_id=False):
        ''' Create an invoice with a single line. '''
        invoice_vals = {
            'move_type': invoice_type,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': partner_id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': amount,
                'tax_ids': [],
            })],
        }
        if currency_id:
            invoice_vals['currency_id'] = currency_id

        invoices = self.env['account.move'].create(
            [invoice_vals for n in range(num_invoices)])
        invoices.action_post()
        return invoices

    def _create_payment(self, amount, partner_id, payment_type, num_payments=1, currency_id=False):
        payment_vals = {
            'payment_type': payment_type,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': partner_id,
            'amount': amount,
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
        }
        if currency_id:
            payment_vals['currency_id'] = currency_id

        payments = self.env['account.payment'].create(
            [payment_vals for n in range(num_payments)])
        payments.action_post()
        return payments

    def _create_statement_line(self, amount, partner_id):
        statement_vals = {
            'date': '2017-01-01',
            'partner_id': partner_id,
            'amount': amount,
            'payment_ref': 'test',
            'journal_id': self.company_data['default_journal_bank'].id,
        }

        statement_lines = self.env['account.bank.statement.line'].create(statement_vals)
        return statement_lines

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
            'currency_id': self.currency_data['currency'].id,
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
            'currency_id': self.currency_data['currency'].id,
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

    def test_two_invoices_one_statement(self):
        ''' Test the payments widget on invoices with a statement line that has a write-off.
        In this case we have two invoices with one statement line.'''
        # Create two invoices with the same amount, same partner
        invoice_1, invoice_2 = self._create_invoice(
            40.0, partner_id=self.partner_a.id, invoice_type='out_invoice', num_invoices=2)
        to_reconcile = (invoice_1 + invoice_2).line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
        # Create a statement line with a write-off
        statement_line = self._create_statement_line(
            78.0, partner_id=self.partner_a.id)
        # Create a dummy line for the second invoice
        statement_line.move_id.write({
            'line_ids': [
                Command.create({
                    'account_id': statement_line.move_id.journal_id.suspense_account_id.id,
                    'partner_id': self.partner_a.id,
                    'balance': 0.0,
                }),
            ],
        })
        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _liquidity_line, suspense_lines, _other_line = statement_line._seek_for_lines()
        # Update the suspense lines and add the write-off
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_lines[0].id, {
                    'account_id': to_reconcile.account_id.id,
                    'balance': -40.0,
                }),
                Command.update(suspense_lines[1].id, {
                    'account_id': to_reconcile.account_id.id,
                    'balance': -40.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })

        (suspense_lines + to_reconcile).reconcile()
        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [39.0, 1.0],
                'amount_company_currency': '$ 80.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice_1, expected_amounts)
        self.assert_compare_invoice_widgets(invoice_2, expected_amounts)

    def test_one_invoice_one_payment_one_statement(self):
        ''' Test the payments widget on an invoice with a payment and a statement line that has a write-off.
        1 invoice <-> 1 payment <-> 1 statement line
        '''
        invoice = self._create_invoice(
            40.0, partner_id=self.partner_a.id, invoice_type='out_invoice')[0]
        payment = self._create_payment(
            40.0, partner_id=self.partner_a.id, payment_type='inbound')[0]
        (payment.move_id + invoice).line_ids.filtered(lambda x: x.account_id ==
                                                      self.company_data['default_account_receivable']).reconcile()
        # At first the invoice widget should contain payment data
        expected_amounts = {payment.move_id.id: 40.0}
        self.assert_invoice_outstanding_reconciled_widget(
            invoice, expected_amounts)

        statement_line = self._create_statement_line(
            38.0, partner_id=self.partner_a.id)
        pay_liquidity_line, _pay_counterpart_line, _pay_writeoff_lines = payment._seek_for_lines()
        _liquidity_line, suspense_line, _other_lines = statement_line._seek_for_lines()
        # Update the statement to include a write-off
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_line.id, {
                    'account_id': pay_liquidity_line.account_id.id,
                    'balance': -40.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })
        # Reconcile the statement line with payment
        (suspense_line + pay_liquidity_line).reconcile()

        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [38.0, 2.0],
                'amount_company_currency': '$ 40.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice, expected_amounts)

    def test_two_invoices_one_payment_one_statement(self):
        ''' Test the payments widget on two invoices with a payment and a statement line that has a write-off.
        2 invoices <-> 1 payment <-> 1 statement line
        '''
        invoice_1, invoice_2 = self._create_invoice(
            40.0, partner_id=self.partner_a.id, invoice_type='out_invoice', num_invoices=2)
        payment = self._create_payment(
            80.0, partner_id=self.partner_a.id, payment_type='inbound')[0]
        (payment.move_id + invoice_1 + invoice_2).line_ids.filtered(lambda x: x.account_id ==
                                                                    self.company_data['default_account_receivable']).reconcile()
        # At first the invoice widget should contain payment data
        expected_amounts = {payment.move_id.id: 40.0}
        self.assert_invoice_outstanding_reconciled_widget(
            invoice_1, expected_amounts)
        self.assert_invoice_outstanding_reconciled_widget(
            invoice_2, expected_amounts)

        statement_line = self._create_statement_line(
            78.0, partner_id=self.partner_a.id)
        pay_liquidity_line, _pay_counterpart_line, _pay_writeoff_lines = payment._seek_for_lines()
        _liquidity_line, suspense_line, _other_lines = statement_line._seek_for_lines()
        # Update the statement to include the write-off
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_line.id, {
                    'account_id': pay_liquidity_line.account_id.id,
                    'balance': -80.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })
        # Reconcile the statement line with payment
        (suspense_line + pay_liquidity_line).reconcile()

        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [39.0, 1.0],
                'amount_company_currency': '$ 80.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice_1, expected_amounts)
        self.assert_compare_invoice_widgets(invoice_2, expected_amounts)

    def test_one_invoice_two_payments_one_statement(self):
        ''' Test the payments widget on one invoice with two payments and a statement line that has a write-off.
        1 invoice <-> 2 payments <-> 1 statement line
        '''
        invoice = self._create_invoice(
            40.0, partner_id=self.partner_a.id, invoice_type='out_invoice')[0]
        payment_1, payment_2 = self._create_payment(
            20.0, partner_id=self.partner_a.id, payment_type='inbound', num_payments=2)
        (payment_1.move_id + payment_2.move_id + invoice).line_ids.filtered(lambda x: x.account_id ==
                                                                            self.company_data['default_account_receivable']).reconcile()
        # At first the invoice widget should contain payment data
        expected_amounts = {payment_1.move_id.id: 20.0,
                            payment_2.move_id.id: 20.0}
        self.assert_invoice_outstanding_reconciled_widget(
            invoice, expected_amounts)

        statement_line = self._create_statement_line(
            38.0, partner_id=self.partner_a.id)

        pay_1_liquidity_line, _pay_1_counterpart_line, _pay_1_writeoff_lines = payment_1._seek_for_lines()
        pay_2_liquidity_line, _pay_2_counterpart_line, _pay_2_writeoff_lines = payment_2._seek_for_lines()
        # Create a dummy suspense line for the second payment
        statement_line.move_id.write({
            'line_ids': [
                Command.create({
                    'account_id': statement_line.move_id.journal_id.suspense_account_id.id,
                    'partner_id': self.partner_a.id,
                    'balance': 0.0,
                }),
            ],
        })
        _liquidity_line, suspense_lines, _other_lines = statement_line._seek_for_lines()
        # Update the statement to include the write-off and balance the payment lines
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_lines[0].id, {
                    'account_id': pay_1_liquidity_line.account_id.id,
                    'balance': -20.0,
                }),
                Command.update(suspense_lines[1].id, {
                    'account_id': pay_2_liquidity_line.account_id.id,
                    'balance': -20.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })
        # Reconcile the statement line with payments
        (suspense_lines + pay_1_liquidity_line + pay_2_liquidity_line).reconcile()

        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [38.0, 2.0],
                'amount_company_currency': '$ 40.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice, expected_amounts)

    def test_foreign_currency_invoice_payment_statement(self):
        ''' Test the payments widget on the invoice issued in a foreign currency, that has a payment in a foreign currency
        and a statement line in company currency.
        '''
        invoice = self._create_invoice(40.0, partner_id=self.partner_a.id,
                                       currency_id=self.currency_data['currency'].id, invoice_type='out_invoice')[0]
        payment = self._create_payment(40.0, partner_id=self.partner_a.id,
                                       currency_id=self.currency_data['currency'].id, payment_type='inbound')[0]
        (payment.move_id + invoice).line_ids.filtered(lambda x: x.account_id ==
                                                      self.company_data['default_account_receivable']).reconcile()
        # At first the invoice widget should contain payment data
        expected_amounts = {payment.move_id.id: 40.0}
        self.assert_invoice_outstanding_reconciled_widget(
            invoice, expected_amounts)

        statement_line = self._create_statement_line(
            18.0, partner_id=self.partner_a.id)
        pay_liquidity_line, _pay_counterpart_line, _pay_writeoff_lines = payment._seek_for_lines()
        _liquidity_line, suspense_line, _other_lines = statement_line._seek_for_lines()
        # Add the write-off
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_line.id, {
                    'account_id': pay_liquidity_line.account_id.id,
                    'balance': -20.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })
        # Reconcile the statement line with payment
        (suspense_line + pay_liquidity_line).reconcile()

        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [36.0, 4.0],
                'amount_company_currency': '$ 20.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice, expected_amounts)

    def test_foreign_currency_invoice_statement(self):
        ''' Test the payments widget on the invoice issued in a foreign currency, that has a statement line in company currency.
        '''
        invoice = self._create_invoice(40.0, partner_id=self.partner_a.id,
                                       currency_id=self.currency_data['currency'].id, invoice_type='out_invoice')[0]
        to_reconcile = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
        statement_line = self._create_statement_line(
            18.0, partner_id=self.partner_a.id)
        _liquidity_line, suspense_line, _other_line = statement_line._seek_for_lines()
        # Add the write-off and balance the suspense line
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_line.id, {
                    'account_id': to_reconcile.account_id.id,
                    'balance': -20.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })
        (suspense_line + to_reconcile).reconcile()
        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [36.0, 4.0],
                'amount_company_currency': '$ 20.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice, expected_amounts)

    def test_foreign_currency_two_invoices_statement(self):
        '''Test the payments widget on two invoices issued in a foreign currency, that are reconciled with one statement
        line in company currency.
        '''
        invoice_1, invoice_2 = self._create_invoice(
            40.0, partner_id=self.partner_a.id, currency_id=self.currency_data['currency'].id, invoice_type='out_invoice', num_invoices=2)
        to_reconcile = (invoice_1 + invoice_2).mapped('line_ids').filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
        statement_line = self._create_statement_line(
            38.0, partner_id=self.partner_a.id)
        # Create a dummy line for the second invoice, so it can be balanced later
        statement_line.move_id.write({
            'line_ids': [
                Command.create({
                    'account_id': statement_line.move_id.journal_id.suspense_account_id.id,
                    'partner_id': self.partner_a.id,
                    'balance': 0.0,
                }),
            ],
        })
        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _liquidity_line, suspense_lines, _other_line = statement_line._seek_for_lines()
        # Update the suspense lines and add the write-off
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_lines[0].id, {
                    'account_id': to_reconcile.account_id.id,
                    'balance': -20.0,
                }),
                Command.update(suspense_lines[1].id, {
                    'account_id': to_reconcile.account_id.id,
                    'balance': -20.0,
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'balance': 2.0,
                }),
            ],
        })

        (suspense_lines + to_reconcile).reconcile()

        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [38.0, 2.0],
                'amount_company_currency': '$ 40.00',
            }
        }
        self.assert_compare_invoice_widgets(invoice_1, expected_amounts)
        self.assert_compare_invoice_widgets(invoice_2, expected_amounts)

    def test_multicurrency_flow_with_payments(self):
        # Create an invoice with the following receivable lines:
        # - 360 GOLD    120 USD     (30%)
        # - 840 GOLD    280 USD     (70%)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_b.id, # 30% in advance, then 70%.
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1200.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        receivable_lines = invoice.line_ids.filtered(lambda l: l.account_type == 'asset_receivable')

        # A payment with a write-off paying 180 USD.
        # - 120.0 USD   (liquidity line)
        # - 90.0 USD    (write-off)
        # This payment is tricky because:
        # - This payment will be reconciled in the invoice in foreign currency since the invoice has a foreign currency
        # but not the payment.
        # - 210 USD will be reconciled with the invoice due to the write-off.
        # - 2 partials will be generated because 210 USD is more than the first 30% to pay.
        # - An exchange difference line will be generated on the payment.
        payment1 = self.env['account.payment'].create({
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'amount': 120.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'write_off_line_vals': [{
                'name': "A write-off line to mimic the mark as fully paid from the payment wizard",
                'account_id': self.company_data['default_account_revenue'].id,
                'partner_id': self.partner_a.id,
                'amount_currency': 90.0,
                'balance': 90.0,
            }],
        })
        payment1.action_post()
        pay1_liquidity_line, pay1_counterpart_line, _pay1_writeoff_lines = payment1._seek_for_lines()

        # A payment paying more than the residual amount of the invoice in a third currency:
        # - 1800.0 STAR     300.0 USD
        # There is only 240 USD left on the invoice after the reconciliation with payment1.
        payment2 = self.env['account.payment'].create({
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data_2['currency'].id,
            'amount': 1800.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        payment2.action_post()
        pay2_liquidity_line, pay2_counterpart_line, _pay2_writeoff_lines = payment2._seek_for_lines()

        # A statement line to pay both payments (one in USD, other in STAR) expressed in GOLD but a write-off in USD.
        # We need:
        # - 300 GOLD    120 USD (to pay payment1)
        # - 750 GOLD    300 USD (to pay payment2)
        # The rate (2.5:1) is custom and provided by the bank.
        # The write-off is expressed in USD so no foreign currency here.
        statement_line = self.env['account.bank.statement.line'].create({
            'date': '2017-01-01',
            'payment_ref': "test",
            'journal_id': self.company_data['default_journal_bank'].id,
            'partner_id': self.partner_a.id,
            'foreign_currency_id': self.currency_data['currency'].id,
            'amount': 450.0,
            'amount_currency': 1125.0,
        })

        _liquidity_line, suspense_line, _other_lines = statement_line._seek_for_lines()
        statement_line.move_id.write({
            'line_ids': [
                Command.update(suspense_line.id, {
                    'account_id': pay1_liquidity_line.account_id.id,
                    'amount_currency': -1050.0, # 300 + 750
                    'balance': -420.0, # 120 + 300
                }),
                Command.create({
                    'name': "Write-off line",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_a.id,
                    'currency_id': self.company_data['currency'].id,
                    'amount_currency': -30.0,
                    'balance': -30.0,
                }),
            ],
        })

        # Reconcile with payment1.
        (receivable_lines + pay1_counterpart_line).reconcile()
        self.assertRecordValues(
            # pylint: disable=bad-whitespace
            receivable_lines + pay1_counterpart_line,
            [
                # (1) Partial:
                # amount: 120 USD
                # debit_amount_currency: 360 GOLD
                # credit_amount_currency: 120 USD
                {'amount_residual': 0.0,    'amount_residual_currency': 0.0},
                # (2) Partial:
                # amount: 20 USD
                # debit_amount_currency: 60 GOLD
                # credit_amount_currency: 20 USD
                {'amount_residual': 260.0,  'amount_residual_currency': 780.0},
                # (1) Partial: See above.
                # (2) Partial: See above.
                # Partial exchange diff for (1):
                # amount: 60 USD
                # debit_amount_currency: 60 USD
                # credit_amount_currency: 60 USD
                # Partial exchange diff for (2):
                # amount: 10 USD
                # debit_amount_currency: 10 USD
                # credit_amount_currency: 10 USD
                {'amount_residual': 0.0,    'amount_residual_currency': 0.0},
            ],
        )

        # Reconcile with payment2.
        (receivable_lines[1] + pay2_counterpart_line).reconcile()
        self.assertRecordValues(
            # pylint: disable=bad-whitespace
            receivable_lines[1] + pay2_counterpart_line,
            [
                # (1) Partial: See above.
                # (2) Partial: See above.
                # (3) Partial:
                # amount: 260 USD
                # debit_amount_currency: 780 GOLD
                # credit_amount_currency: 1560 STAR
                {'amount_residual': 0.0,    'amount_residual_currency': 0.0},
                # (3) Partial: See above.
                {'amount_residual': -40.0,  'amount_residual_currency': -240.0},
            ],
        )

        # Reconcile the statement line with the payments.
        (suspense_line + pay1_liquidity_line + pay2_liquidity_line).reconcile()
        self.assertRecordValues(
            # pylint: disable=bad-whitespace
            suspense_line + pay1_liquidity_line + pay2_liquidity_line,
            [
                {'amount_residual': 0.0,    'amount_residual_currency': 0.0},
                # (4) Partial:
                # amount: 120 USD
                # debit_amount_currency: 120 USD
                # credit_amount_currency: 300 GOLD
                {'amount_residual': 0.0,    'amount_residual_currency': 0.0},
                # (5) Partial:
                # amount: 300 USD
                # debit_amount_currency: 1800 STAR
                # credit_amount_currency: 750 GOLD
                {'amount_residual': 0.0,    'amount_residual_currency': 0.0},
            ],
        )
        exchange_move_ids = [ln.matched_credit_ids.exchange_move_id.id for ln in invoice.line_ids if ln.matched_credit_ids.exchange_move_id]
        expected_amounts = {
            statement_line.move_id.id: {
                'amount': [1140.0, 60],
                'amount_company_currency': '$ 450.00',
            },
            exchange_move_ids[0]: {
                'amount': [60.0],
                'amount_company_currency': '$ 60.00',
            },
            exchange_move_ids[1]: {
                'amount': [10.0],
                'amount_company_currency': '$ 10.00',
            },
        }
        self.assert_compare_invoice_widgets(invoice, expected_amounts)
