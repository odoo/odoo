# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestAccountPayment(AccountPaymentCommon):

    def test_no_amount_available_for_refund_when_no_tx(self):
        payment = self.env['account.payment'].create({'amount': 10})
        self.assertEqual(
            payment.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when the payment was not"
                " created by a transaction."
        )

    def test_no_amount_available_for_refund_when_not_supported(self):
        self.provider.support_refund = 'none'
        tx = self._create_transaction('redirect', state='done')
        tx._post_process()  # Create the payment
        self.assertEqual(
            tx.payment_id.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when the provider doesn't "
                "support refunds."
        )

    def test_full_amount_available_for_refund_when_not_yet_refunded(self):
        self.provider.support_refund = 'full_only'  # Should simply not be False
        tx = self._create_transaction('redirect', state='done')
        tx._post_process()  # Create the payment
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
        tx._post_process()  # Create the payment
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
        tx._post_process()  # Create the payment
        self._create_transaction(
            'dummy',
            amount=-tx.amount,
            reference=f'R-{tx.reference}',
            state='done',
            operation='refund',  # Override the computed flow
            source_transaction_id=tx.id,
        )._post_process()
        self.assertEqual(
            tx.payment_id.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when there is a linked "
                "refund of the full amount that is confirmed (state 'done')."
        )

    def test_no_full_amount_available_for_refund_when_partially_refunded(self):
        self.provider.support_refund = 'partial'
        tx = self._create_transaction('redirect', state='done')
        tx._post_process()  # Create the payment
        self._create_transaction(
            'dummy',
            amount=-(tx.amount / 10),
            reference=f'R-{tx.reference}',
            state='done',
            operation='refund',  # Override the computed flow
            source_transaction_id=tx.id,
        )._post_process()
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
        tx._post_process()  # Create the payment
        for reference_index, operation in enumerate(
            ('online_redirect', 'online_direct', 'online_token', 'validation', 'refund')
        ):
            self._create_transaction(
                'dummy',
                reference=f'R-{tx.reference}-{reference_index + 1}',
                state='done',
                operation=operation,  # Override the computed flow
                source_transaction_id=tx.id,
            )._post_process()

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
        tx._post_process()
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
        child_tx_1._post_process()
        self.assertTrue(child_tx_1.payment_id, msg="Child transactions should create payments.")
        source_tx._post_process()
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
            payment_method_line.payment_account_id = self.inbound_payment_method_line.payment_account_id
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

    def test_generate_payment_link_with_no_invoice_line(self):
        invoice = self.invoice
        invoice.line_ids.unlink()
        payment_values = invoice._get_default_payment_link_values()

        self.assertDictEqual(payment_values, {
            'currency_id': invoice.currency_id.id,
            'partner_id': invoice.partner_id.id,
            'open_installments': [],
            'installment_state': None,
            'amount': None,
            'amount_max': None,
        })
