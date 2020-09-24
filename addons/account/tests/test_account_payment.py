# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payment_debit_account_id = cls.copy_account(cls.company_data['default_journal_bank'].payment_debit_account_id)
        cls.payment_credit_account_id = cls.copy_account(cls.company_data['default_journal_bank'].payment_credit_account_id)

        cls.partner_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'BE32707171912447',
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })

        cls.company_data['default_journal_bank'].write({
            'payment_debit_account_id': cls.payment_debit_account_id.id,
            'payment_credit_account_id': cls.payment_credit_account_id.id,
            'inbound_payment_method_ids': [(6, 0, cls.env.ref('account.account_payment_method_manual_in').ids)],
            'outbound_payment_method_ids': [(6, 0, cls.env.ref('account.account_payment_method_manual_out').ids)],
        })

        cls.partner_a.write({
            'bank_ids': [(6, 0, cls.partner_bank_account.ids)],
        })

    def test_payment_move_sync_create_write(self):
        copy_receivable = self.copy_account(self.company_data['default_account_receivable'])

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'destination_account_id': copy_receivable.id,
        })

        expected_payment_values = {
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': False,
            'destination_account_id': copy_receivable.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_bank_id': False,
        }
        expected_move_values = {
            'currency_id': self.company_data['currency'].id,
            'partner_id': False,
            'partner_bank_id': False,
        }
        expected_liquidity_line = {
            'debit': 50.0,
            'credit': 0.0,
            'amount_currency': 50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': self.payment_debit_account_id.id,
        }
        expected_counterpart_line = {
            'debit': 0.0,
            'credit': 50.0,
            'amount_currency': -50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': copy_receivable.id,
        }

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

        # ==== Check editing the account.payment ====

        payment.write({
            'partner_type': 'supplier',
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,
        })

        self.assertRecordValues(payment, [{
            **expected_payment_values,
            'partner_type': 'supplier',
            'destination_account_id': self.partner_a.property_account_payable_id.id,
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,
            'partner_bank_id': self.partner_bank_account.id,
        }])
        self.assertRecordValues(payment.move_id, [{
            **expected_move_values,
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,
            'partner_bank_id': self.partner_bank_account.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                **expected_counterpart_line,
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -50.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': self.partner_a.property_account_payable_id.id,
            },
            {
                **expected_liquidity_line,
                'debit': 25.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.currency_data['currency'].id,
            },
        ])

        # ==== Check editing the account.move.line ====

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
        payment.move_id.write({
            'partner_bank_id': False,
            'line_ids': [
                (1, counterpart_lines.id, {
                    'debit': 0.0,
                    'credit': 75.0,
                    'amount_currency': -75.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': copy_receivable.id,
                    'partner_id': self.partner_b.id,
                }),
                (1, liquidity_lines.id, {
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 100.0,
                    'currency_id': self.company_data['currency'].id,
                    'partner_id': self.partner_b.id,
                }),

                # Additional write-off:
                (0, 0, {
                    'debit': 0.0,
                    'credit': 25.0,
                    'amount_currency': -25.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'partner_id': self.partner_b.id,
                }),
            ]
        })

        self.assertRecordValues(payment, [{
            **expected_payment_values,
            'amount': 100.0,
            'partner_id': self.partner_b.id,
        }])
        self.assertRecordValues(payment.move_id, [{
            **expected_move_values,
            'partner_id': self.partner_b.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                **expected_counterpart_line,
                'debit': 0.0,
                'credit': 75.0,
                'amount_currency': -75.0,
                'partner_id': self.partner_b.id,
            },
            {
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -25.0,
                'currency_id': self.company_data['currency'].id,
                'account_id': self.company_data['default_account_revenue'].id,
                'partner_id': self.partner_b.id,
            },
            {
                **expected_liquidity_line,
                'debit': 100.0,
                'credit': 0.0,
                'amount_currency': 100.0,
                'account_id': self.payment_debit_account_id.id,
                'partner_id': self.partner_b.id,
            },
        ])

    def test_payment_move_sync_onchange(self):
        copy_receivable = self.copy_account(self.company_data['default_account_receivable'])

        pay_form = Form(self.env['account.payment'].with_context(default_journal_id=self.company_data['default_journal_bank'].id))
        pay_form.amount = 50.0
        pay_form.payment_type = 'inbound'
        pay_form.partner_type = 'customer'
        pay_form.destination_account_id = copy_receivable
        payment = pay_form.save()

        expected_payment_values = {
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': False,
            'destination_account_id': copy_receivable.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
        }
        expected_move_values = {
            'currency_id': self.company_data['currency'].id,
            'partner_id': False,
        }
        expected_liquidity_line = {
            'debit': 50.0,
            'credit': 0.0,
            'amount_currency': 50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': self.payment_debit_account_id.id,
        }
        expected_counterpart_line = {
            'debit': 0.0,
            'credit': 50.0,
            'amount_currency': -50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': copy_receivable.id,
        }

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

        # ==== Check editing the account.payment ====

        pay_form = Form(payment)
        pay_form.partner_type = 'supplier'
        pay_form.currency_id = self.currency_data['currency']
        pay_form.partner_id = self.partner_a
        payment = pay_form.save()

        self.assertRecordValues(payment, [{
            **expected_payment_values,
            'partner_type': 'supplier',
            'destination_account_id': self.partner_a.property_account_payable_id.id,
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,
        }])
        self.assertRecordValues(payment.move_id, [{
            **expected_move_values,
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                **expected_counterpart_line,
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -50.0,
                'currency_id': self.currency_data['currency'].id,
                'account_id': self.partner_a.property_account_payable_id.id,
            },
            {
                **expected_liquidity_line,
                'debit': 25.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.currency_data['currency'].id,
            },
        ])

        # ==== Check editing the account.move.line ====

        move_form = Form(payment.move_id)
        with move_form.line_ids.edit(0) as line_form:
            line_form.currency_id = self.company_data['currency']
            line_form.amount_currency = 100.0
            line_form.partner_id = self.partner_b
        with move_form.line_ids.edit(1) as line_form:
            line_form.currency_id = self.company_data['currency']
            line_form.amount_currency = -75.0
            line_form.account_id = copy_receivable
            line_form.partner_id = self.partner_b
        with move_form.line_ids.new() as line_form:
            line_form.currency_id = self.company_data['currency']
            line_form.amount_currency = -25.0
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.partner_id = self.partner_b
        move_form.save()

        self.assertRecordValues(payment, [{
            **expected_payment_values,
            'amount': 100.0,
            'partner_id': self.partner_b.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                **expected_counterpart_line,
                'debit': 0.0,
                'credit': 75.0,
                'amount_currency': -75.0,
                'partner_id': self.partner_b.id,
            },
            {
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -25.0,
                'currency_id': self.company_data['currency'].id,
                'account_id': self.company_data['default_account_revenue'].id,
                'partner_id': self.partner_b.id,
            },
            {
                **expected_liquidity_line,
                'debit': 100.0,
                'credit': 0.0,
                'amount_currency': 100.0,
                'account_id': self.payment_debit_account_id.id,
                'partner_id': self.partner_b.id,
            },
        ])

    def test_internal_transfer(self):
        copy_receivable = self.copy_account(self.company_data['default_account_receivable'])

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'is_internal_transfer': True,
        })

        expected_payment_values = {
            'amount': 50.0,
            'payment_type': 'inbound',
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.company_data['company'].partner_id.id,
            'destination_account_id': self.company_data['company'].transfer_account_id.id,
        }
        expected_move_values = {
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.company_data['company'].partner_id.id,
        }
        expected_liquidity_line = {
            'debit': 50.0,
            'credit': 0.0,
            'amount_currency': 50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': self.payment_debit_account_id.id,
        }
        expected_counterpart_line = {
            'debit': 0.0,
            'credit': 50.0,
            'amount_currency': -50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': self.company_data['company'].transfer_account_id.id,
        }

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

        # ==== Check editing the account.payment ====

        payment.write({
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'destination_account_id': copy_receivable.id,
        })

        self.assertRecordValues(payment, [{
            **expected_payment_values,
            'partner_type': 'customer',
            'destination_account_id': copy_receivable.id,
            'partner_id': self.partner_a.id,
            'is_internal_transfer': False,
        }])
        self.assertRecordValues(payment.move_id, [{
            **expected_move_values,
            'partner_id': self.partner_a.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                **expected_counterpart_line,
                'account_id': copy_receivable.id,
            },
            expected_liquidity_line,
        ])

        # ==== Check editing the account.move.line ====

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
        payment.move_id.write({
            'line_ids': [
                (1, counterpart_lines.id, {
                    'account_id': self.company_data['company'].transfer_account_id.id,
                    'partner_id': self.company_data['company'].partner_id.id,
                }),
                (1, liquidity_lines.id, {
                    'partner_id': self.company_data['company'].partner_id.id,
                }),
            ]
        })

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

    def test_compute_currency_id(self):
        ''' When creating a new account.payment without specifying a currency, the default currency should be the one
        set on the journal.
        '''
        self.company_data['default_journal_bank'].write({
            'currency_id': self.currency_data['currency'].id,
        })

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_bank'].id,
        })

        self.assertRecordValues(payment, [{
            'currency_id': self.currency_data['currency'].id,
        }])
        self.assertRecordValues(payment.move_id, [{
            'currency_id': self.currency_data['currency'].id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -50.0,
                'currency_id': self.currency_data['currency'].id,
            },
            {
                'debit': 25.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.currency_data['currency'].id,
            },
        ])

    def test_reconciliation_payment_states(self):
        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'destination_account_id': self.company_data['default_account_receivable'].id,
        })
        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()

        self.assertRecordValues(payment, [{
            'is_reconciled': False,
            'is_matched': False,
        }])

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': '50 to pay',
                'price_unit': 50.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })

        payment.action_post()
        invoice.action_post()

        (counterpart_lines + invoice.line_ids.filtered(lambda line: line.account_internal_type == 'receivable'))\
            .reconcile()

        self.assertRecordValues(payment, [{
            'is_reconciled': True,
            'is_matched': False,
        }])

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {
                    'payment_ref': '50 to pay',
                    'partner_id': self.partner_a.id,
                    'amount': 50.0,
                }),
            ],
        })
        statement.button_post()
        statement_line = statement.line_ids

        statement_line.reconcile([{'id': liquidity_lines.id}])

        self.assertRecordValues(payment, [{
            'is_reconciled': True,
            'is_matched': True,
        }])
