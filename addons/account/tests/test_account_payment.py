# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company = cls.company_data['default_journal_bank'].company_id

        cls.payment_debit_account_id = cls.copy_account(company.account_journal_payment_debit_account_id)
        cls.payment_credit_account_id = cls.copy_account(company.account_journal_payment_credit_account_id)

        cls.bank_journal_1 = cls.company_data['default_journal_bank']
        cls.bank_journal_2 = cls.company_data['default_journal_bank'].copy()

        cls.partner_bank_account1 = cls.env['res.partner.bank'].create({
            'acc_number': "0123456789",
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })
        cls.partner_bank_account2 = cls.env['res.partner.bank'].create({
            'acc_number': "9876543210",
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })
        cls.comp_bank_account1 = cls.env['res.partner.bank'].create({
            'acc_number': "985632147",
            'partner_id': cls.env.company.partner_id.id,
            'acc_type': 'bank',
        })
        cls.comp_bank_account2 = cls.env['res.partner.bank'].create({
            'acc_number': "741258963",
            'partner_id': cls.env.company.partner_id.id,
            'acc_type': 'bank',
        })

        company.write({
            'account_journal_payment_debit_account_id': cls.payment_debit_account_id.id,
            'account_journal_payment_credit_account_id': cls.payment_credit_account_id.id
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
            'payment_method_line_id': self.inbound_payment_method_line.id,
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

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
        payment.move_id.write({
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

    def test_payment_move_sync_update_journal_custom_accounts(self):
        """The objective is to edit the journal of a payment in order to check if the accounts are updated."""

        company = self.company_data['company']
        # Create two different inbound accounts
        outstanding_payment_A = company.account_journal_payment_debit_account_id
        outstanding_payment_B = company.account_journal_payment_debit_account_id.copy()
        # Create two different journals with a different account
        journal_A = self.company_data['default_journal_bank']
        journal_A.inbound_payment_method_line_ids.payment_account_id = outstanding_payment_A
        journal_B = self.company_data['default_journal_bank'].copy()
        journal_B.inbound_payment_method_line_ids.payment_account_id = outstanding_payment_B

        # Fill the form payment
        pay_form = Form(self.env['account.payment'].with_context(default_journal_id=self.company_data['default_journal_bank'].id))
        pay_form.amount = 50.0
        pay_form.payment_type = 'inbound'
        pay_form.partner_id = self.partner_a
        pay_form.journal_id = journal_A
        # Save the form (to create move and move line)
        payment = pay_form.save()

        # Check the payment
        self.assertRecordValues(payment, [{
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
            'journal_id': journal_A.id
        }])
        self.assertRecordValues(payment.move_id, [{
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
            'journal_id': journal_A.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 50.0,
                'amount_currency': -50.0,
                'currency_id': self.company_data['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 50.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.company_data['currency'].id,
                'account_id': outstanding_payment_A.id,
            },
        ])

        # Change the journal on the form
        pay_form.journal_id = journal_B
        # Save the form (to write move and move line)
        payment = pay_form.save()

        # Check the payment
        self.assertRecordValues(payment, [{
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
            'journal_id': journal_B.id
        }])
        self.assertRecordValues(payment.move_id, [{
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
            'journal_id': journal_B.id,
        }])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 50.0,
                'amount_currency': -50.0,
                'currency_id': self.company_data['currency'].id,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 50.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.company_data['currency'].id,
                'account_id': outstanding_payment_B.id,
            },
        ])

    def test_payment_move_sync_onchange(self):

        pay_form = Form(self.env['account.payment'].with_context(
            default_journal_id=self.company_data['default_journal_bank'].id,
            # The `partner_type` is set through the window action context in the web client
            # the field is otherwise invisible in the form.
            default_partner_type='customer',
        ))
        pay_form.amount = 50.0
        pay_form.payment_type = 'inbound'
        pay_form.partner_id = self.partner_a
        payment = pay_form.save()

        expected_payment_values = {
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
            'destination_account_id': self.partner_a.property_account_receivable_id.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }
        expected_move_values = {
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
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
            'account_id': self.company_data['default_account_receivable'].id,
        }

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

        # ==== Check editing the account.payment ====

        # `partner_type` on payment is always invisible. It's supposed to be set through a context `default_` key
        # In this case the goal of the test is to take an existing customer payment and change it to a supplier payment,
        # which is not supposed to be possible through the web interface.
        # So, change the payment partner_type beforehand rather than in the form view.
        payment.partner_type = 'supplier'
        pay_form = Form(payment)
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
            line_form.partner_id = self.partner_b
            line_form.account_id = self.company_data['default_account_receivable']
        with move_form.line_ids.new() as line_form:
            line_form.currency_id = self.company_data['currency']
            line_form.amount_currency = -25.0
            line_form.partner_id = self.partner_b
            line_form.account_id = self.company_data['default_account_revenue']
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

    def test_inbound_payment_sync_writeoff_debit_sign(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })

        # ==== Edit the account.move.line ====

        liquidity_lines, counterpart_lines, dummy = payment._seek_for_lines()
        payment.move_id.write({
            'line_ids': [
                (1, liquidity_lines.id, {'debit': 100.0}),
                (1, counterpart_lines.id, {'credit': 125.0}),
                (0, 0, {'debit': 25.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        self.assertRecordValues(payment, [{
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 100.0,
        }])

        # ==== Edit the account.payment amount ====

        payment.write({
            'partner_type': 'supplier',
            'amount': 100.1,
            'destination_account_id': self.company_data['default_account_payable'].id,
        })

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 125.1,
                'account_id': self.company_data['default_account_payable'].id,
            },
            {
                'debit': 25.0,
                'credit': 0.0,
                'account_id': self.company_data['default_account_revenue'].id,
            },
            {
                'debit': 100.1,
                'credit': 0.0,
                'account_id': self.payment_debit_account_id.id,
            },
        ])

    def test_inbound_payment_sync_writeoff_credit_sign(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })

        # ==== Edit the account.move.line ====

        liquidity_lines, counterpart_lines, dummy = payment._seek_for_lines()
        payment.move_id.write({
            'line_ids': [
                (1, liquidity_lines.id, {'debit': 100.0}),
                (1, counterpart_lines.id, {'credit': 75.0}),
                (0, 0, {'credit': 25.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        self.assertRecordValues(payment, [{
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 100.0,
        }])

        # ==== Edit the account.payment amount ====

        payment.write({
            'partner_type': 'supplier',
            'amount': 100.1,
            'destination_account_id': self.company_data['default_account_payable'].id,
        })

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 75.1,
                'account_id': self.company_data['default_account_payable'].id,
            },
            {
                'debit': 0.0,
                'credit': 25.0,
                'account_id': self.company_data['default_account_revenue'].id,
            },
            {
                'debit': 100.1,
                'credit': 0.0,
                'account_id': self.payment_debit_account_id.id,
            },
        ])

    def test_outbound_payment_sync_writeoff_debit_sign(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
        })

        # ==== Edit the account.move.line ====

        liquidity_lines, counterpart_lines, dummy = payment._seek_for_lines()
        payment.move_id.write({
            'line_ids': [
                (1, liquidity_lines.id, {'credit': 100.0}),
                (1, counterpart_lines.id, {'debit': 75.0}),
                (0, 0, {'debit': 25.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        self.assertRecordValues(payment, [{
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
        }])

        # ==== Edit the account.payment amount ====

        payment.write({
            'partner_type': 'customer',
            'amount': 100.1,
            'destination_account_id': self.company_data['default_account_receivable'].id,
        })

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 100.1,
                'account_id': self.payment_credit_account_id.id,
            },
            {
                'debit': 25.0,
                'credit': 0.0,
                'account_id': self.company_data['default_account_revenue'].id,
            },
            {
                'debit': 75.1,
                'credit': 0.0,
                'account_id': self.company_data['default_account_receivable'].id,
            },
        ])

    def test_outbound_payment_sync_writeoff_credit_sign(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
        })

        # ==== Edit the account.move.line ====

        liquidity_lines, counterpart_lines, dummy = payment._seek_for_lines()
        payment.move_id.write({
            'line_ids': [
                (1, liquidity_lines.id, {'credit': 100.0}),
                (1, counterpart_lines.id, {'debit': 125.0}),
                (0, 0, {'credit': 25.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        self.assertRecordValues(payment, [{
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
        }])

        # ==== Edit the account.payment amount ====

        payment.write({
            'partner_type': 'customer',
            'amount': 100.1,
            'destination_account_id': self.company_data['default_account_receivable'].id,
        })

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 100.1,
                'account_id': self.payment_credit_account_id.id,
            },
            {
                'debit': 0.0,
                'credit': 25.0,
                'account_id': self.company_data['default_account_revenue'].id,
            },
            {
                'debit': 125.1,
                'credit': 0.0,
                'account_id': self.company_data['default_account_receivable'].id,
            },
        ])

    def test_internal_transfer(self):
        copy_receivable = self.copy_account(self.company_data['default_account_receivable'])

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'is_internal_transfer': True,
            'destination_journal_id': self.company_data['default_journal_cash'].id,
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

        # ==== Check creation of paired internal transfer payment ====

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'is_internal_transfer': True,
            'payment_type': 'inbound',
            'destination_journal_id': self.company_data['default_journal_cash'].id,
        })
        payment.action_post()
        paired_payment = self.env['account.payment'].search([('payment_type', '=', 'outbound')])
        expected_payment_values = {
            'amount': 50.0,
            'payment_type': 'outbound',
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.company_data['company'].partner_id.id,
            'destination_account_id': self.company_data['company'].transfer_account_id.id,
        }
        expected_move_values = {
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.company_data['company'].partner_id.id,
        }
        expected_liquidity_line = {
            'debit': 0.0,
            'credit': 50.0,
            'amount_currency': -50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': self.company_data['default_journal_cash'].company_id.account_journal_payment_credit_account_id.id,
        }
        expected_counterpart_line = {
            'debit': 50.0,
            'credit': 0.0,
            'amount_currency': 50.0,
            'currency_id': self.company_data['currency'].id,
            'account_id': self.company_data['company'].transfer_account_id.id,
        }

        self.assertRecordValues(paired_payment, [expected_payment_values])
        self.assertRecordValues(paired_payment.move_id, [expected_move_values])
        self.assertRecordValues(paired_payment.line_ids.sorted('balance'), [
            expected_liquidity_line,
            expected_counterpart_line,
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

        (counterpart_lines + invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable'))\
            .reconcile()

        self.assertRecordValues(payment, [{
            'is_reconciled': True,
            'is_matched': False,
        }])

        statement_line = self.env['account.bank.statement.line'].create({
            'payment_ref': '50 to pay',
            'journal_id': self.company_data['default_journal_bank'].id,
            'partner_id': self.partner_a.id,
            'amount': 50.0,
        })

        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _st_liquidity_lines, st_suspense_lines, _st_other_lines = statement_line\
            .with_context(skip_account_move_synchronization=True)\
            ._seek_for_lines()
        st_suspense_lines.account_id = liquidity_lines.account_id
        (st_suspense_lines + liquidity_lines).reconcile()

        self.assertRecordValues(payment, [{
            'is_reconciled': True,
            'is_matched': True,
        }])

    def test_payment_name(self):
        AccountPayment = self.env['account.payment']
        AccountPayment.search([]).unlink()

        payment = AccountPayment.create({
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        self.assertRegex(payment.name, r'BNK1/\d{4}/00001')

        with Form(AccountPayment.with_context(default_move_journal_types=('bank', 'cash'))) as payment_form:
            self.assertEqual(payment_form.name, '/')
            payment_form.journal_id = self.company_data['default_journal_cash']
            self.assertRegex(payment_form.name, r'CSH1/\d{4}/00001')
            payment_form.journal_id = self.company_data['default_journal_bank']
        payment = payment_form.save()
        self.assertEqual(payment.name, '/')
        payment.action_post()
        self.assertRegex(payment.name, r'BNK1/\d{4}/00002')

    def test_payment_without_default_company_account(self):
        """ The purpose of this test is to check the specific behavior when duplicating an inbound payment, then change
        the copy to an outbound payment when we set the outstanding accounts (payments and receipts) on a journal but
        not on the company level.
        """
        company = self.company_data['company']
        bank_journal = self.company_data['default_journal_bank']

        bank_journal.outbound_payment_method_line_ids.payment_account_id = company.account_journal_payment_credit_account_id
        bank_journal.inbound_payment_method_line_ids.payment_account_id = company.account_journal_payment_debit_account_id
        company.account_journal_payment_debit_account_id = False
        company.account_journal_payment_credit_account_id = False

        payment = self.env['account.payment'].create({
            'amount': 5.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': bank_journal.id,
        })
        self.assertRecordValues(payment, [{
            'amount': 5.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': False,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])

        payment.payment_type = 'outbound'
        self.assertRecordValues(payment, [{
            'amount': 5.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': False,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        }])

    def test_suggested_default_partner_bank(self):
        """ Ensure the 'partner_bank_id' is well computed on payments. When the payment is inbound, the money must be
        received by a bank account linked to the company. In case of outbound payment, the bank account must be found
        on the partner.
        """
        payment = self.env['account.payment'].create({
            'journal_id': self.bank_journal_1.id,
            'amount': 50.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_a.id,
        })
        self.assertRecordValues(payment, [{
            'available_partner_bank_ids': self.partner_a.bank_ids.ids,
            'partner_bank_id': self.partner_bank_account1.id,
        }])

        payment.payment_type = 'inbound'
        self.assertRecordValues(payment, [{
            'available_partner_bank_ids': [],
            'partner_bank_id': False,
        }])

        self.bank_journal_2.bank_account_id = self.comp_bank_account2
        # A sequence is automatically added on the first move. We need to clean it before changing the journal.
        payment.name = False
        payment.journal_id = self.bank_journal_2
        self.assertRecordValues(payment, [{
            'available_partner_bank_ids': self.comp_bank_account2.ids,
            'partner_bank_id': self.comp_bank_account2.id,
        }])

    def test_internal_transfer_right_accounts(self):
        """The purpose of this test is to check that the right accounts are computed when making an internal bank transfer"""

        company = self.env.company
        transfer_account = company.transfer_account_id
        bank = self.bank_journal_1
        bank_2 = self.bank_journal_2

        payment = self.env['account.payment'].create({
            'is_internal_transfer': True,
            'payment_type': 'outbound',
            'amount': 100.0,
            'journal_id': bank.id,
            'destination_journal_id': bank_2.id,
        })
        payment.action_post()

        self.assertRecordValues(payment.line_ids, [
            {'account_id': company.account_journal_payment_credit_account_id.id},
            {'account_id': transfer_account.id},
        ])
        self.assertRecordValues(payment.paired_internal_transfer_payment_id.line_ids, [
            {'account_id': company.account_journal_payment_debit_account_id.id},
            {'account_id': transfer_account.id},
        ])

        # We check the behavior when setting specific receipts/payments account on bank journals
        bank.inbound_payment_method_line_ids.payment_account_id = company.account_journal_payment_debit_account_id.copy({'code': 1001})
        bank.outbound_payment_method_line_ids.payment_account_id = company.account_journal_payment_credit_account_id.copy({'code': 1002})

        bank_2.inbound_payment_method_line_ids.payment_account_id = company.account_journal_payment_debit_account_id.copy({'code': 2001})
        bank_2.outbound_payment_method_line_ids.payment_account_id = company.account_journal_payment_credit_account_id.copy({'code': 2002})

        payment = self.env['account.payment'].create({
            'is_internal_transfer': True,
            'payment_type': 'outbound',
            'amount': 100.0,
            'journal_id': bank.id,
            'destination_journal_id': bank_2.id,
        })
        payment.action_post()

        self.assertRecordValues(payment.line_ids, [
            {'account_id': bank.outbound_payment_method_line_ids.payment_account_id.id,},
            {'account_id': transfer_account.id},
        ])
        self.assertRecordValues(payment.paired_internal_transfer_payment_id.line_ids, [
            {'account_id': bank_2.inbound_payment_method_line_ids.payment_account_id.id},
            {'account_id': transfer_account.id},
        ])
