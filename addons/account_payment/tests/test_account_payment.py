# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestAccountPayment(AccountPaymentCommon):

    def test_no_amount_available_for_refund_when_not_supported(self):
        self.provider.support_refund = False
        tx = self._create_transaction('redirect', state='done')
        tx._reconcile_after_done()  # Create the payment
        self.assertEqual(
            tx.payment_id.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when the provider doesn't "
                "support refunds."
        )

    def test_full_amount_available_for_refund_when_not_yet_refunded(self):
        self.provider.support_refund = 'full_only'  # Should simply not be False
        tx = self._create_transaction('redirect', state='done')
        tx._reconcile_after_done()  # Create the payment
        self.assertAlmostEqual(
            tx.payment_id.amount_available_for_refund,
            tx.amount,
            places=2,
            msg="The value of `amount_available_for_refund` should be that of `total` when there "
                "are no linked refunds."
        )

    def test_full_amount_available_for_refund_when_refunds_are_pending(self):
        self.provider.write({
            'support_refund': 'full_only',  # Should simply not be False
            'support_manual_capture': 'partial',  # To create transaction in the 'authorized' state
        })
        tx = self._create_transaction('redirect', state='done')
        tx._reconcile_after_done()  # Create the payment
        for reference_index, state in enumerate(('draft', 'pending', 'authorized')):
            self._create_transaction(
                'dummy',
                amount=-tx.amount,
                reference=f'R-{tx.reference}-{reference_index + 1}',
                state=state,
                operation='refund',  # Override the computed flow
                source_transaction_id=tx.id,
            )
        self.assertAlmostEqual(
            tx.payment_id.amount_available_for_refund,
            tx.payment_id.amount,
            places=2,
            msg="The value of `amount_available_for_refund` should be that of `total` when all the "
                "linked refunds are pending (not in the state 'done')."
        )

    def test_no_amount_available_for_refund_when_fully_refunded(self):
        self.provider.support_refund = 'full_only'  # Should simply not be False
        tx = self._create_transaction('redirect', state='done')
        tx._reconcile_after_done()  # Create the payment
        self._create_transaction(
            'dummy',
            amount=-tx.amount,
            reference=f'R-{tx.reference}',
            state='done',
            operation='refund',  # Override the computed flow
            source_transaction_id=tx.id,
        )._reconcile_after_done()
        self.assertEqual(
            tx.payment_id.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when there is a linked "
                "refund of the full amount that is confirmed (state 'done')."
        )

    def test_no_full_amount_available_for_refund_when_partially_refunded(self):
        self.provider.support_refund = 'partial'
        tx = self._create_transaction('redirect', state='done')
        tx._reconcile_after_done()  # Create the payment
        self._create_transaction(
            'dummy',
            amount=-(tx.amount / 10),
            reference=f'R-{tx.reference}',
            state='done',
            operation='refund',  # Override the computed flow
            source_transaction_id=tx.id,
        )._reconcile_after_done()
        self.assertAlmostEqual(
            tx.payment_id.amount_available_for_refund,
            tx.payment_id.amount - (tx.amount / 10),
            places=2,
            msg="The value of `amount_available_for_refund` should be equal to the total amount "
                "minus the sum of the absolute amount of the refunds that are confirmed (state "
                "'done')."
        )

    def test_refunds_count(self):
        self.provider.support_refund = 'full_only'  # Should simply not be False
        tx = self._create_transaction('redirect', state='done')
        tx._reconcile_after_done()  # Create the payment
        for reference_index, operation in enumerate(
            ('online_redirect', 'online_direct', 'online_token', 'validation', 'refund')
        ):
            self._create_transaction(
                'dummy',
                reference=f'R-{tx.reference}-{reference_index + 1}',
                state='done',
                operation=operation,  # Override the computed flow
                source_transaction_id=tx.id,
            )._reconcile_after_done()

        self.assertEqual(
            tx.payment_id.refunds_count,
            1,
            msg="The refunds count should only consider transactions with operation 'refund'."
        )

    def test_action_post_calls_send_payment_request_only_once(self):
        payment_token = self._create_token()
        payment_without_token = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 2000.0,
            'date': '2019-01-01',
            'currency_id': self.currency.id,
            'partner_id': self.partner.id,
            'journal_id': self.provider.journal_id.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        payment_with_token = payment_without_token.copy()
        payment_with_token.payment_token_id = payment_token.id

        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._send_payment_request'
        ) as patched:
            payment_without_token.action_post()
            patched.assert_not_called()
            payment_with_token.action_post()
            patched.assert_called_once()

    def test_no_payment_for_validations(self):
        tx = self._create_transaction(flow='dummy', operation='validation')  # Overwrite the flow
        tx._reconcile_after_done()
        payment_count = self.env['account.payment'].search_count(
            [('payment_transaction_id', '=', tx.id)]
        )
        self.assertEqual(payment_count, 0, msg="validation transactions should not create payments")

    def test_payments_for_source_tx_with_children(self):
        self.provider.support_manual_capture = 'partial'
        source_tx = self._create_transaction(flow='direct', state='authorized')
        child_tx_1 = source_tx._create_child_transaction(100)
        child_tx_1._set_done()
        child_tx_2 = source_tx._create_child_transaction(source_tx.amount - 100)
        self.assertEqual(
            source_tx.state,
            'authorized',
            msg="The source transaction should be authorized when the total processed amount of its"
                " children is not equal to the source amount.",
        )
        child_tx_2._set_canceled()
        self.assertEqual(
            source_tx.state,
            'done',
            msg="The source transaction should be done when the total processed amount of its"
                " children is equal to the source amount.",
        )
        child_tx_2._reconcile_after_done()
        self.assertTrue(child_tx_2.payment_id, msg="Child transactions should create payments.")
        source_tx._reconcile_after_done()
        self.assertFalse(
            source_tx.payment_id,
            msg="source transactions with done or cancel children should not create payments.",
        )

    def test_prevent_unlink_apml_with_active_provider(self):
        """ Deleting an account.payment.method.line that is related to a provider in 'test' or 'enabled' state
        should raise an error.
        """
        self.assertEqual(self.dummy_provider.state, 'test')
        with self.assertRaises(UserError):
            self.dummy_provider.journal_id.inbound_payment_method_line_ids.unlink()

    def test_provider_journal_assignation(self):
        """ Test the computation of the 'journal_id' field and so, the link with the accounting side. """
        def get_payment_method_line(provider):
            return self.env['account.payment.method.line'].search([('payment_provider_id', '=', provider.id)])

        with self.mocked_get_payment_method_information():
            journal = self.company_data['default_journal_bank']
            provider = self.provider
            self.assertRecordValues(provider, [{'journal_id': journal.id}])

            # Test changing the journal.
            copy_journal = journal.copy()
            payment_method_line = get_payment_method_line(provider)
            provider.journal_id = copy_journal
            self.assertRecordValues(provider, [{'journal_id': copy_journal.id}])
            self.assertRecordValues(payment_method_line, [{'journal_id': copy_journal.id}])

            # Test duplication of the provider.
            payment_method_line.payment_account_id = self.env.company.account_journal_payment_debit_account_id
            copy_provider = self.provider.copy()
            self.assertRecordValues(copy_provider, [{'journal_id': False}])
            copy_provider.state = 'test'
            self.assertRecordValues(copy_provider, [{'journal_id': journal.id}])
            self.assertRecordValues(get_payment_method_line(copy_provider), [{
                'journal_id': journal.id,
                'payment_account_id': payment_method_line.payment_account_id.id,
            }])

            # We are able to have both on the same journal...
            with self.assertRaises(ValidationError):
                # ...but not having both with the same name.
                provider.journal_id = journal

            method_line = get_payment_method_line(copy_provider)
            method_line.name = "dummy (copy)"
            provider.journal_id = journal

            # You can't have twice the same acquirer on the same journal.
            copy_provider_pml = get_payment_method_line(copy_provider)
            with self.assertRaises(ValidationError):
                journal.inbound_payment_method_line_ids = [Command.update(copy_provider_pml.id, {'payment_provider_id': provider.id})]

    #   ////////////////////////////////////////////////////////
    #   Tests for payments with early payments discount
    #   ///////////////////////////////////////////////////////
    def _create_payment_term_with_early_discount(self, **kwargs):
        return self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'company_id': self.company_data['company'].id,
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            **kwargs,
        })

    def _create_invoice_with_early_discount(self, payment_term_id=None, **kwargs):
        invoice_with_early_discount = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': datetime.now().date(),
            'currency_id': self.currency.id,
            'invoice_payment_term_id': payment_term_id or self._create_payment_term_with_early_discount().id,
            'invoice_line_ids': [Command.create({
                'name': 'test line',
                'price_unit': 100.0,
                'tax_ids': [],
            })],
            **kwargs
        })
        invoice_with_early_discount.action_post()
        return invoice_with_early_discount

    def assert_invoice_payment(self, payment, invoice, expected_values):
        self.assertEqual(payment.amount, expected_values['payment_amount'])
        self.assertEqual(payment.amount_total, expected_values['payment_amount_total'])
        self.assertEqual(invoice.payment_state, expected_values['invoice_payment_state'])
        self.assertEqual(invoice.amount_paid, expected_values['invoice_amount_paid'])
        self.assertRecordValues(payment.line_ids, expected_values['payment_line_ids'])

    def test_eligible_invoice_no_tax(self):
        """
        This test verifies the correct application of early payment discount on an eligible invoice without taxes.
        """
        invoice_eligible = self._create_invoice_with_early_discount()
        payment = self._create_transaction(
            reference='payment_1',
            flow='direct',
            state='done',
            amount=invoice_eligible.invoice_payment_term_id._get_amount_due_after_discount(
                total_amount=invoice_eligible.amount_residual,      # 100.0
                untaxed_amount=invoice_eligible.amount_tax,         # 0.0
            ),                                                      # 90.0
            invoice_ids=[invoice_eligible.id],
        )._create_payment()

        self.assert_invoice_payment(
            payment=payment,
            invoice=invoice_eligible,
            expected_values={
                'payment_amount': 90.0,
                'payment_amount_total': 100.0,
                'invoice_payment_state': invoice_eligible._get_invoice_in_payment_state(),
                'invoice_amount_paid': 90.0,
                'payment_line_ids': [
                    {'credit': 0.0, 'debit': 90.0, 'account_type': 'asset_current'},
                    {'credit': 100, 'debit': 0.0, 'account_type': 'asset_receivable'},
                    {'credit': 0, 'debit': 10.0, 'account_type': 'expense'},
                ],
            }
        )

    def test_ineligible_invoice_past_discount_date(self):
        """
        This test ensures no discount is applied to an invoice past the early payment discount date.
        """
        invoice_ineligible = self._create_invoice_with_early_discount(invoice_date=(datetime.now() - timedelta(days=30)).date())
        payment = self._create_transaction(
            reference='payment_2',
            flow='direct',
            state='done',
            amount=invoice_ineligible.amount_residual,  # 100.0
            invoice_ids=[invoice_ineligible.id],
        )._create_payment()

        self.assert_invoice_payment(
            payment=payment,
            invoice=invoice_ineligible,
            expected_values={
                'payment_amount': 100.0,
                'payment_amount_total': 100.0,
                'invoice_payment_state': invoice_ineligible._get_invoice_in_payment_state(),
                'invoice_amount_paid': 100.0,
                'payment_line_ids': [
                    {'credit': 0.0, 'debit': 100.0, 'account_type': 'asset_current'},
                    {'credit': 100, 'debit': 0.0, 'account_type': 'asset_receivable'},
                ],
            }
        )

    def test_eligible_invoice_with_tax(self):
        """
        This test checks the correct calculation of early payment discount on an eligible invoice with taxes.
        """
        invoice_eligible_with_tax = self._create_invoice_with_early_discount(
            invoice_line_ids=[Command.create({
                'name': 'test line',
                'price_unit': 100.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],  # 15%
            })],
        )
        payment = self._create_transaction(
            reference='payment_3',
            flow='direct',
            state='done',
            amount=invoice_eligible_with_tax.invoice_payment_term_id._get_amount_due_after_discount(
                total_amount=invoice_eligible_with_tax.amount_residual,     # 100.0
                untaxed_amount=invoice_eligible_with_tax.amount_tax,        # 15.0
            ),                                                              # 115.0 - 10% -> 115 * (1 - 0.1) = 103.5
            invoice_ids=[invoice_eligible_with_tax.id],
        )._create_payment()

        self.assert_invoice_payment(
            payment=payment,
            invoice=invoice_eligible_with_tax,
            expected_values={
                'payment_amount': 103.5,
                'payment_amount_total': 115.0,
                'invoice_payment_state': invoice_eligible_with_tax._get_invoice_in_payment_state(),
                'invoice_amount_paid': 103.5,
                'payment_line_ids': [
                    {'credit': 0.0, 'debit': 103.5, 'account_type': 'asset_current'},
                    {'credit': 115, 'debit': 0.0, 'account_type': 'asset_receivable'},
                    {'credit': 0, 'debit': 10.0, 'account_type': 'expense'},
                    {'credit': 0, 'debit': 1.5, 'account_type': 'liability_current'},
                ],
            }
        )

    def test_ineligible_invoice_mixed_discount_computation_and_tax(self):
        """
        This test validates the behavior of mixed discount computation on an ineligible invoice with taxes.
        The early discount should be applied on the untaxed amount past the early payment discount date.
        "The tax is always reduced. The base amount used to compute the tax is the discounted amount,
        whether the customer benefits from the discount or not." (cf Cash discounts and tax reduction documentation)
        """
        payment_term_with_mixed_discount_computation = self._create_payment_term_with_early_discount(
            early_pay_discount_computation='mixed',
        )
        invoice_ineligible_with_mixed_and_tax = self._create_invoice_with_early_discount(
            payment_term_id=payment_term_with_mixed_discount_computation.id,
            invoice_date=(datetime.now() - timedelta(days=30)).date(),
            invoice_line_ids=[Command.create({
                'name': 'test line',
                'price_unit': 100.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],  # 15%
            })],
        )
        payment = self._create_transaction(
            reference='payment_4',
            flow='direct',
            state='done',
            amount=invoice_ineligible_with_mixed_and_tax.amount_residual,  # 100 + (15 * (1 - 0.1)) = 113.5
            invoice_ids=[invoice_ineligible_with_mixed_and_tax.id],
        )._create_payment()

        self.assert_invoice_payment(
            payment=payment,
            invoice=invoice_ineligible_with_mixed_and_tax,
            expected_values={
                'payment_amount': 113.5,
                'payment_amount_total': 113.5,
                'invoice_payment_state': invoice_ineligible_with_mixed_and_tax._get_invoice_in_payment_state(),
                'invoice_amount_paid': 113.5,
                'payment_line_ids': [
                    {'credit': 0.0, 'debit': 113.5, 'account_type': 'asset_current'},
                    {'credit': 113.5, 'debit': 0.0, 'account_type': 'asset_receivable'},
                ],
            }
        )

    def test_eligible_invoice_excluded_discount_computation_and_tax(self):
        """
        This test validates the behavior of excluded discount computation method on an eligible invoice with taxes.
        "The tax is never reduced. The base amount used to compute the tax is the full amount,
        whether the customer benefits from the discount or not." (cf Cash discounts and tax reduction documentation)
        """
        payment_term_with_excluded_discount_computation = self._create_payment_term_with_early_discount(
            early_pay_discount_computation='excluded',
        )
        invoice_eligible_with_excluded_and_tax = self._create_invoice_with_early_discount(
            payment_term_id=payment_term_with_excluded_discount_computation.id,
            invoice_line_ids=[Command.create({
                'name': 'test line',
                'price_unit': 100.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],  # 15%
            })],
        )
        payment = self._create_transaction(
            reference='payment_5',
            flow='direct',
            state='done',
            amount=invoice_eligible_with_excluded_and_tax.invoice_payment_term_id._get_amount_due_after_discount(
                total_amount=invoice_eligible_with_excluded_and_tax.amount_residual,    # 100.0
                untaxed_amount=invoice_eligible_with_excluded_and_tax.amount_tax,       # 15.0
            ),                                                                          # (100 - 10%), 90 + 15 = 105
            invoice_ids=[invoice_eligible_with_excluded_and_tax.id],
        )._create_payment()

        self.assert_invoice_payment(
            payment=payment,
            invoice=invoice_eligible_with_excluded_and_tax,
            expected_values={
                'payment_amount': 105.0,
                'payment_amount_total': 115.0,
                'invoice_payment_state': invoice_eligible_with_excluded_and_tax._get_invoice_in_payment_state(),
                'invoice_amount_paid': 105.0,
                'payment_line_ids': [
                    {'credit': 0.0, 'debit': 105.0, 'account_type': 'asset_current'},
                    {'credit': 115, 'debit': 0.0, 'account_type': 'asset_receivable'},
                    {'credit': 0, 'debit': 10.0, 'account_type': 'expense'},
                ],
            }
        )

    def test_eligible_invoice_foreign_currency(self):
        """
        This test checks the correct calculation of early payment discount on an eligible invoice in a foreign currency.
        """
        foreign_currency = self.currency_data['currency']  # Gold Coin currency
        invoice_eligible_with_foreign_currency = self._create_invoice_with_early_discount(
            currency_id=foreign_currency.id,
            company_currency_id=self.currency.id,
        )
        payment = self._create_transaction(
            reference='payment_6',
            flow='direct',
            state='done',
            amount=invoice_eligible_with_foreign_currency.invoice_payment_term_id._get_amount_due_after_discount(
                total_amount=invoice_eligible_with_foreign_currency.amount_residual,    # 100.0 gold    / 50.0$
                untaxed_amount=invoice_eligible_with_foreign_currency.amount_tax,       # 0.0 gold      / 0.0$
            ),                                                                          # 90.0 gold     / 45.0$
            currency_id=foreign_currency.id,
            invoice_ids=[invoice_eligible_with_foreign_currency.id],
        )._create_payment()

        self.assert_invoice_payment(
            payment=payment,
            invoice=invoice_eligible_with_foreign_currency,
            expected_values={
                'payment_amount': 90,
                'payment_amount_total': 100,
                'invoice_payment_state': invoice_eligible_with_foreign_currency._get_invoice_in_payment_state(),
                'invoice_amount_paid': 90,
                'payment_line_ids': [
                    {'credit': 0.0, 'debit': 45.0, 'account_type': 'asset_current'},
                    {'credit': 50.0, 'debit': 0.0, 'account_type': 'asset_receivable'},
                    {'credit': 0, 'debit': 5.0, 'account_type': 'expense'},
                ],
            }
        )

    def test_payment_invoice_same_receivable(self):
        """
        Test that when creating a payment transaction, the payment uses the same account_id as the related invoice
        and not the partner accound_id
        """
        invoice = self._create_invoice_with_early_discount(
            invoice_line_ids=[
                Command.create({
                    'name': 'test line',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
                Command.create({
                    'name': 'test line 2',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        )
        self.partner.property_account_receivable_id = self.env['account.account'].search([('name', '=', 'Account Payable')], limit=1)
        payment = self._create_transaction(
            reference='payment_3',
            flow='direct',
            state='done',
            amount=invoice.invoice_payment_term_id._get_amount_due_after_discount(
                total_amount=invoice.amount_residual,
                untaxed_amount=invoice.amount_tax,
            ),
            invoice_ids=[invoice.id],
            partner_id=self.partner.id,
        )._create_payment()

        self.assertNotEqual(self.partner.property_account_receivable_id, payment.payment_id.destination_account_id)
        self.assertEqual(payment.payment_id.destination_account_id, invoice.line_ids[-1].account_id)
