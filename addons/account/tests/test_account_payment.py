# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.tests.common import Form
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountMovePayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_journal.default_credit_account_id = cls.bank_journal.default_debit_account_id.copy()

        cls.cash_journal = cls.company_data['default_journal_cash']
        cls.cash_journal.default_credit_account_id = cls.cash_journal.default_debit_account_id.copy()

        cls.inbound_payment = cls._init_payment(cls, 'inbound', partner_type='customer')
        cls.outbound_payment = cls._init_payment(cls, 'outbound', partner_type='supplier')
        cls.transfer_payment = cls._init_payment(cls, 'transfer')

    @staticmethod
    def _init_payment(cls, payment_type, partner_type=None):
        payment_form = Form(cls.env['account.payment'])
        payment_form.journal_id = cls.bank_journal
        payment_form.payment_date = fields.Date.from_string('2019-01-01')
        payment_form.amount = 100
        if payment_type == 'transfer':
            payment_form.destination_journal_id = cls.cash_journal
        else:
            payment_form.partner_type = partner_type
            payment_form.partner_id = cls.partner_a
        payment_form.payment_type = payment_type
        return payment_form.save()

    def assertPaymentValues(self, payment, expected_lines_values):
        self.assertRecordValues(payment.move_line_ids.sorted(lambda line: (line.name, line.balance)), expected_lines_values)

    def test_inbound_payment_move_1(self):
        ''' Check created account.move for an account.payment having the 'inbound' type. '''
        liquidity_account = self.bank_journal.default_credit_account_id

        expected_bank_line = {
            'account_id': liquidity_account.id,
            'partner_id': self.partner_a.id,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 100.0,
            'credit': 0.0,
        }
        expected_receivable_line = {
            'account_id': self.inbound_payment.destination_account_id .id,
            'partner_id': self.partner_a.id,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 0.0,
            'credit': 100.0,
        }

        # Single currency.

        self.inbound_payment.post()

        self.assertPaymentValues(self.inbound_payment, [
            expected_bank_line,
            expected_receivable_line,
        ])

        # Multi currencies: Foreign currency on payment.

        self.inbound_payment.action_draft()
        self.inbound_payment.currency_id = self.currency_data['currency']
        self.inbound_payment.post()

        self.assertPaymentValues(self.inbound_payment, [
            {
                **expected_bank_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 100.0,
                'debit': 50.0,
            },
            {
                **expected_receivable_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -100.0,
                'credit': 50.0,
            },
        ])

        self.inbound_payment.currency_id = self.company_data['currency']

        # Multi currencies: Foreign currency on journal.

        self.inbound_payment.action_draft()
        self.inbound_payment.journal_id.currency_id = self.currency_data['currency']
        self.inbound_payment.post()

        self.assertPaymentValues(self.inbound_payment, [
            {
                **expected_bank_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
            },
            expected_receivable_line,
        ])

    def test_outbound_payment_move_1(self):
        ''' Check created account.move for an account.payment having the 'outbound' type. '''
        liquidity_account = self.bank_journal.default_debit_account_id

        expected_bank_line = {
            'account_id': liquidity_account.id,
            'partner_id': self.partner_a.id,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 0.0,
            'credit': 100.0,
        }
        expected_payable_line = {
            'account_id': self.outbound_payment.destination_account_id.id,
            'partner_id': self.partner_a.id,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 100.0,
            'credit': 0.0,
        }

        # Single currency.

        self.outbound_payment.post()

        self.assertPaymentValues(self.outbound_payment, [
            expected_bank_line,
            expected_payable_line,
        ])

        # Multi currencies: Foreign currency on payment.

        self.outbound_payment.action_draft()
        self.outbound_payment.currency_id = self.currency_data['currency']
        self.outbound_payment.post()

        self.assertPaymentValues(self.outbound_payment, [
            {
                **expected_bank_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -100.0,
                'credit': 50.0,
            },
            {
                **expected_payable_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 100.0,
                'debit': 50.0,
            },
        ])

        self.outbound_payment.currency_id = self.company_data['currency']

        # Multi currencies: Foreign currency on journal.

        self.outbound_payment.action_draft()
        self.outbound_payment.journal_id.currency_id = self.currency_data['currency']
        self.outbound_payment.post()

        self.assertPaymentValues(self.outbound_payment, [
            {
                **expected_bank_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            expected_payable_line,
        ])

    def test_transfer_payment_move_1(self):
        ''' Check created account.move for an account.payment having the 'transfer' type. '''
        liquidity_bank_account = self.bank_journal.default_debit_account_id
        liquidity_cash_account = self.cash_journal.default_credit_account_id

        cash_transfer_line = {
            'account_id': self.company_data['company'].transfer_account_id.id,
            'partner_id': False,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 0.0,
            'credit': 100.0,
        }
        bank_transfer_line = {
            'account_id': self.company_data['company'].transfer_account_id.id,
            'partner_id': False,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 100.0,
            'credit': 0.0,
        }
        liquidity_cash_line = {
            'account_id': liquidity_cash_account.id,
            'partner_id': False,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 100.0,
            'credit': 0.0,
        }
        liquidity_bank_line = {
            'account_id': liquidity_bank_account.id,
            'partner_id': False,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 0.0,
            'credit': 100.0,
        }

        # Single currency.

        self.transfer_payment.post()

        self.assertPaymentValues(self.transfer_payment, [
            cash_transfer_line,
            bank_transfer_line,
            liquidity_cash_line,
            liquidity_bank_line,
        ])

        # Multi currencies: Foreign currency on payment.

        self.transfer_payment.action_draft()
        self.transfer_payment.currency_id = self.currency_data['currency']
        self.transfer_payment.post()

        self.assertPaymentValues(self.transfer_payment, [
            {
                **cash_transfer_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -100.0,
                'credit': 50.0,
            },
            {
                **bank_transfer_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 100.0,
                'debit': 50.0,
            },
            {
                **liquidity_cash_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 100.0,
                'debit': 50.0,
            },
            {
                **liquidity_bank_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -100.0,
                'credit': 50.0,
            },
        ])

        self.transfer_payment.currency_id = self.company_data['currency']

        # Multi currencies: Foreign currency on journal.

        self.transfer_payment.action_draft()
        self.transfer_payment.journal_id.currency_id = self.currency_data['currency']
        self.transfer_payment.destination_journal_id.currency_id = self.currency_data['currency']
        self.transfer_payment.post()

        self.assertPaymentValues(self.transfer_payment, [
            {
                **cash_transfer_line,
                'credit': 100.0,
            },
            {
                **bank_transfer_line,
                'debit': 100.0,
            },
            {
                **liquidity_cash_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
            },
            {
                **liquidity_bank_line,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
        ])
