# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        cls.payment_debit_account_id = cls.inbound_payment_method_line.payment_account_id
        cls.payment_credit_account_id = cls.outbound_payment_method_line.payment_account_id

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

        cls.pay_term_epd = cls.env['account.payment.term'].create([{
            'name': "test",
            'early_discount': True,
            'discount_percentage': 10,
            'discount_days': 10,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 30,
                }),
            ],
        }])

    def test_payment_move_sync_create_write(self):
        copy_receivable = self.copy_account(self.company_data['default_account_receivable'])

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'destination_account_id': copy_receivable.id,
        })
        payment.action_post()

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
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

    def test_payment_move_sync_update_journal_custom_accounts(self):
        """The objective is to edit the journal of a payment in order to check if the accounts are updated."""

        # Create two different inbound accounts
        outstanding_payment_A = self.inbound_payment_method_line.payment_account_id
        outstanding_payment_B = self.inbound_payment_method_line.payment_account_id.copy()
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
        payment.action_post()

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
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
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
        payment.action_post()

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
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            expected_counterpart_line,
            expected_liquidity_line,
        ])

        # ==== Check editing the account.payment ====
        # `partner_type` on payment is always invisible. It's supposed to be set through a context `default_` key
        # In this case the goal of the test is to take an existing customer payment and change it to a supplier payment,
        # which is not supposed to be possible through the web interface.
        # So, change the payment partner_type beforehand rather than in the form view.
        payment.action_draft()
        payment.partner_type = 'supplier'
        pay_form = Form(payment)
        pay_form.currency_id = self.other_currency
        payment = pay_form.save()
        self.assertRecordValues(payment, [{
            **expected_payment_values,
            'partner_type': 'supplier',
            'destination_account_id': self.partner_a.property_account_payable_id.id,
            'currency_id': self.other_currency.id,
            'partner_id': self.partner_a.id,
        }])
        self.assertRecordValues(payment.move_id, [{
            **expected_move_values,
            'currency_id': self.other_currency.id,
            'partner_id': self.partner_a.id,
        }])
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            {
                **expected_counterpart_line,
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -50.0,
                'currency_id': self.other_currency.id,
                'account_id': self.partner_a.property_account_payable_id.id,
            },
            {
                **expected_liquidity_line,
                'debit': 25.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.other_currency.id,
            },
        ])

    def test_payment_journal_onchange(self):
        # Create a new payment form
        pay_form = Form(self.env['account.payment'].with_context(
            default_journal_id=self.company_data['default_journal_bank'].id,
            default_partner_type='customer'
        ))
        pay_form.amount = 50.0
        pay_form.payment_type = 'inbound'
        pay_form.partner_id = self.partner_a
        payment = pay_form.save()

        with self.assertRaises(AssertionError):
            pay_form.journal_id = self.env['account.journal']
            payment = pay_form.save()

        # Check the values of the payment record after the onchange method
        self.assertRecordValues(payment, [{
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_reference': False,
            'is_reconciled': False,
            'currency_id': self.company_data['currency'].id,
            'partner_id': self.partner_a.id,
            'destination_account_id': self.partner_a.property_account_receivable_id.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
            'journal_id': self.company_data['default_journal_bank'].id,
        }])

    def test_compute_currency_id(self):
        ''' When creating a new account.payment without specifying a currency, the default currency should be the one
        set on the journal.
        '''
        self.company_data['default_journal_bank'].currency_id = self.other_currency
        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = self.inbound_payment_method_line.payment_account_id

        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        payment.action_post()

        self.assertRecordValues(payment, [{
            'currency_id': self.other_currency.id,
        }])
        self.assertRecordValues(payment.move_id, [{
            'currency_id': self.other_currency.id,
        }])
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            {
                'debit': 0.0,
                'credit': 25.0,
                'amount_currency': -50.0,
                'currency_id': self.other_currency.id,
            },
            {
                'debit': 25.0,
                'credit': 0.0,
                'amount_currency': 50.0,
                'currency_id': self.other_currency.id,
            },
        ])

    def test_reconciliation_payment_states(self):
        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'destination_account_id': self.company_data['default_account_receivable'].id,
        })
        payment.action_post()
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

    def test_reconciliation_payment_states_reverse_payment_move(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice.action_post()

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})\
            ._create_payments()

        self.assertTrue(invoice.payment_state in ('paid', 'in_payment'))
        self.assertRecordValues(payment, [{'reconciled_invoice_ids': invoice.ids}])

        # Reverse the payment move
        reversal_wizard = self.env['account.move.reversal']\
            .with_context(active_model='account.move', active_ids=payment.move_id.ids)\
            .create({'reason': "oopsie", 'journal_id': payment.journal_id.id})
        reversal_wizard.refund_moves()
        self.assertRecordValues(invoice, [{'payment_state': 'not_paid'}])
        self.assertRecordValues(payment.move_id.line_ids, [{'reconciled': True}] * 2)

    def test_payment_without_default_company_account(self):
        """ The purpose of this test is to check the specific behavior when duplicating an inbound payment, then change
        the copy to an outbound payment when we set the outstanding accounts (payments and receipts) on a journal but
        not on the company level.
        """
        bank_journal = self.company_data['default_journal_bank']

        bank_journal.outbound_payment_method_line_ids.payment_account_id = self.outbound_payment_method_line.payment_account_id.copy()
        bank_journal.inbound_payment_method_line_ids.payment_account_id = self.inbound_payment_method_line.payment_account_id.copy()

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

    def test_reconciliation_with_old_oustanding_account(self):
        """
        Test the reconciliation of an invoice with a payment after changing the outstanding account of the journal.
        """
        outstanding_account_2 = self.inbound_payment_method_line.payment_account_id.copy()

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': 1150,
        })
        payment.action_post()

        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = outstanding_account_2
        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000.0], taxes=self.env['account.tax'])

        credit_line = payment.move_id.line_ids.filtered(lambda l: l.credit and l.account_id == self.company_data['default_account_receivable'])

        invoice.js_assign_outstanding_line(credit_line.id)
        self.assertTrue(invoice.payment_state in ('in_payment', 'paid'), "Invoice should be paid")
        invoice.button_draft()
        self.assertTrue(invoice.payment_state == 'not_paid', "Invoice should'nt be paid anymore")
        self.assertTrue(invoice.state == 'draft', "Invoice should be draft")

    def test_journal_onchange(self):
        """Ensure that the payment method line is recomputed when switching journal in form view."""

        context = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
        }
        with Form(self.env['account.payment'].with_context(context)) as payment:
            default_journal = payment.journal_id
            self.assertTrue(default_journal)
            self.assertEqual(payment.payment_method_line_id.journal_id.id, default_journal.id)

            other_journal = self.bank_journal_2 if default_journal != self.bank_journal_2 else self.bank_journal_1
            payment.journal_id = other_journal
            self.assertEqual(payment.payment_method_line_id.journal_id.id, other_journal.id)

            payment.journal_id = default_journal
            self.assertEqual(payment.payment_method_line_id.journal_id.id, default_journal.id)

    def test_payments_copy_data(self):
        payment_1, payment_2 = self.env['account.payment'].create([
            {
                'partner_id': self.partner_a.id,
                'amount': 50,
            },
            {
                'partner_id': self.partner_b.id,
                'amount': 100,
            },
        ])
        duplicate_payment_1, duplicate_payment_2 = (payment_1 + payment_2).copy()

        self.assertEqual(duplicate_payment_1.partner_id, payment_1.partner_id)
        self.assertEqual(duplicate_payment_2.partner_id, payment_2.partner_id)

        self.assertEqual(duplicate_payment_1.amount, payment_1.amount)
        self.assertEqual(duplicate_payment_2.amount, payment_2.amount)

    def test_payments_epd_eligible_on_move_with_payment(self):
        """ Ensures that even if a move has a payment registered, the epd will still be eligible if no outstanding account is set on the payment method"""
        invoice1 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2024-01-01',
            'invoice_payment_term_id': self.pay_term_epd.id,
            'invoice_line_ids': [Command.create({
                'name': 'test',
                'quantity': 1,
                'price_unit': 1000,
            })],
        }])
        invoice1.action_post()
        # By default, an outstanding account is set on the bank journal, which will result in a journal entry generation
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice1.ids).create({})._create_payments()
        self.assertFalse(invoice1._is_eligible_for_early_payment_discount(invoice1.currency_id, invoice1.invoice_date))
        # Remove the outstanding account on the payment method line to avoid generating a journal entry on the payment
        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = self.env['account.account']
        invoice2 = invoice1.copy()
        invoice2.action_post()
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice2.ids).create({})._create_payments()

        # In the community edition, a journal entry is created for a payment regardless of whether an outstanding account is set.
        # This removes the eligibility for early payment discount.
        is_accounting_installed = invoice1._get_invoice_in_payment_state() == 'in_payment'

        self.assertEqual(invoice2._is_eligible_for_early_payment_discount(invoice2.currency_id, invoice2.invoice_date), is_accounting_installed)

    def test_payments_invoice_payment_state_without_outstanding_accounts(self):
        """ Ensures that, without outstanding accounts set on the bank journal payment method,
            the payment of the invoice still gets a journal entry in community edition """
        def register_payment_and_assert_state(move, amount, is_community):
            def patched_get_invoice_in_payment_state(self):
                return 'paid' if is_community else 'in_payment'

            with patch.object(self.env.registry['account.move'], '_get_invoice_in_payment_state', patched_get_invoice_in_payment_state):
                payment = self.env['account.payment.register'].with_context(
                    active_model='account.move',
                    active_ids=move.ids
                ).create({'amount': amount})._create_payments()

                self.assertEqual(payment.state, 'paid' if is_community else 'in_process')

        # Remove the outstanding account on the payment method line to avoid generating a journal entry on the payment
        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = self.env['account.account']

        invoice_1 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2024-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'test',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        }])
        invoice_1.action_post()
        register_payment_and_assert_state(invoice_1, 100.0, is_community=True)
        self.assertTrue(invoice_1.matched_payment_ids.move_id)

        invoice_2 = invoice_1.copy()
        invoice_2.action_post()
        register_payment_and_assert_state(invoice_2, 100.0, is_community=False)
        self.assertFalse(invoice_2.matched_payment_ids.move_id)
