# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


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
