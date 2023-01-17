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

        cls.bank_journal_1.write({
            'payment_debit_account_id': cls.payment_debit_account_id.id,
            'payment_credit_account_id': cls.payment_credit_account_id.id,
            'inbound_payment_method_ids': [(6, 0, cls.env.ref('account.account_payment_method_manual_in').ids)],
            'outbound_payment_method_ids': [(6, 0, cls.env.ref('account.account_payment_method_manual_out').ids)],
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

    def test_inbound_payment_sync_writeoff_debit_sign(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })

        # ==== Edit the account.move.line ====

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
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

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
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

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
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

        liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
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

    def test_payment_name(self):
        AccountPayment = self.env['account.payment']
        AccountPayment.search([]).unlink()

        payment = AccountPayment.create({
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        self.assertRegex(payment.name, 'BNK1/\d{4}/\d{2}/0001')

        with Form(AccountPayment.with_context(default_move_journal_types=('bank', 'cash'))) as payment_form:
            self.assertEqual(payment_form._values['name'], '/')
            payment_form.journal_id = self.company_data['default_journal_cash']
            self.assertRegex(payment_form._values['name'], 'CSH1/\d{4}/\d{2}/0001')
            payment_form.journal_id = self.company_data['default_journal_bank']
        payment = payment_form.save()
        self.assertEqual(payment.name, '/')
        payment.action_post()
        self.assertRegex(payment.name, 'BNK1/\d{4}/\d{2}/0002')

    def test_payment_form_onchange_journal(self):
        pay_form = Form(self.env['account.payment'])
        pay_form.journal_id = self.company_data['default_journal_bank']
        pay_form.partner_id = self.partner_a
        pay_form.name = '/'
        pay_form.amount = 123
        pay = pay_form.save()

        self.assertRecordValues(pay.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 123.0,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 123.0,
                'credit': 0.0,
                'account_id': self.company_data['default_journal_bank'].payment_debit_account_id.id,
            },
        ])

        with Form(pay) as pay_form:
            pay_form.journal_id = self.company_data['default_journal_cash']
            pay_form.name = '/'

        self.assertRecordValues(pay.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 123.0,
                'account_id': self.company_data['default_account_receivable'].id,
            },
            {
                'debit': 123.0,
                'credit': 0.0,
                'account_id': self.company_data['default_journal_cash'].payment_debit_account_id.id,
            },
        ])

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

    def test_internal_transfer_custom_partner_bank_id(self):
        """ Ensure partner_bank_id user choice is not systematically ignored by compute method. """
        self.bank_journal_1.bank_account_id = self.comp_bank_account1

        payment = self.env['account.payment'].create({
            'journal_id': self.bank_journal_1.id,
            'amount': 50.0,
            'is_internal_transfer': True,
            'payment_type': 'outbound',
            'partner_bank_id': self.comp_bank_account2.id,
        })
        self.assertRecordValues(payment, [{
            'partner_bank_id': self.comp_bank_account2.id,
        }])

    def test_internal_transfer_change_journal(self):
        self.bank_journal_1.bank_account_id = self.comp_bank_account1

        payment = self.env['account.payment'].create({
            'journal_id': self.bank_journal_1.id,
            'amount': 50.0,
            'is_internal_transfer': True,
            'payment_type': 'outbound',
            'partner_bank_id': self.comp_bank_account2.id,
        })

        # This should not raise an error.
        payment.write({
            'journal_id': self.company_data['default_journal_cash'].id
        })
