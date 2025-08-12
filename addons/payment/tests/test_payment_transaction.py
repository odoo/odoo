# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentCommon):

    def test_capture_allowed_for_authorized_users(self):
        """ Test that users who have access to a transaction can capture it. """
        if not self.env.ref('account.group_account_invoice', raise_if_not_found=False):
            self.skipTest("account needed for test")
        self.provider.support_manual_capture = 'full_only'
        tx = self._create_transaction('redirect', state='authorized')
        user = self._prepare_user(self.internal_user, 'account.group_account_invoice')
        self._assert_does_not_raise(AccessError, tx.with_user(user).action_capture)

    def test_void_allowed_for_authorized_users(self):
        """ Test that users who have access to a transaction can void it. """
        if not self.env.ref('account.group_account_invoice', raise_if_not_found=False):
            self.skipTest("account needed for test")
        self.provider.support_manual_capture = 'full_only'
        tx = self._create_transaction('redirect', state='authorized')
        user = self._prepare_user(self.internal_user, 'account.group_account_invoice')
        self._assert_does_not_raise(AccessError, tx.with_user(user).action_void)

    def test_refund_allowed_for_authorized_users(self):
        """ Test that users who have access to a transaction can refund it. """
        if not self.env.ref('account.group_account_invoice', raise_if_not_found=False):
            self.skipTest("account needed for test")
        self.provider.support_refund = 'full_only'
        tx = self._create_transaction('redirect', state='done')
        user = self._prepare_user(self.internal_user, 'account.group_account_invoice')
        self._assert_does_not_raise(AccessError, tx.with_user(user).action_refund)

    def test_capture_blocked_for_unauthorized_user(self):
        """ Test that users who don't have access to a transaction cannot capture it. """
        self.provider.support_manual_capture = 'full_only'
        tx = self._create_transaction('redirect', state='authorized')
        self.assertRaises(AccessError, tx.with_user(self.internal_user).action_capture)

    def test_void_blocked_for_unauthorized_user(self):
        """ Test that users who don't have access to a transaction cannot void it. """
        self.provider.support_manual_capture = 'full_only'
        tx = self._create_transaction('redirect', state='authorized')
        self.assertRaises(AccessError, tx.with_user(self.internal_user).action_void)

    def test_refund_blocked_for_unauthorized_user(self):
        """ Test that users who don't have access to a transaction cannot refund it. """
        self.provider.support_refund = 'full_only'
        tx = self._create_transaction('redirect', state='done')
        self.assertRaises(AccessError, tx.with_user(self.internal_user).action_refund)

    def test_refunds_count(self):
        self.provider.support_refund = 'full_only'  # Should simply not be False
        tx = self._create_transaction('redirect', state='done')
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
            tx.refunds_count,
            1,
            msg="The refunds count should only consider transactions with operation 'refund'."
        )

    def test_refund_transaction_values(self):
        self.provider.support_refund = 'partial'
        tx = self._create_transaction('redirect', state='done')

        # Test the default values of a full refund transaction
        refund_tx = tx._create_child_transaction(tx.amount, is_refund=True)
        self.assertEqual(
            refund_tx.reference,
            f'R-{tx.reference}',
            msg="The reference of the refund transaction should be the prefixed reference of the "
                "source transaction."
        )
        self.assertLess(
            refund_tx.amount, 0, msg="The amount of a refund transaction should always be negative."
        )
        self.assertAlmostEqual(
            refund_tx.amount,
            -tx.amount,
            places=2,
            msg="The amount of the refund transaction should be taken from the amount of the "
                "source transaction."
        )
        self.assertEqual(
            refund_tx.currency_id,
            tx.currency_id,
            msg="The currency of the refund transaction should be that of the source transaction."
        )
        self.assertEqual(
            refund_tx.operation,
            'refund',
            msg="The operation of the refund transaction should be 'refund'."
        )
        self.assertEqual(
            tx,
            refund_tx.source_transaction_id,
            msg="The refund transaction should be linked to the source transaction."
        )
        self.assertEqual(
            refund_tx.partner_id,
            tx.partner_id,
            msg="The partner of the refund transaction should be that of the source transaction."
        )

        # Test the values of a partial refund transaction with custom refund amount
        partial_refund_tx = tx._create_child_transaction(11.11, is_refund=True)
        self.assertAlmostEqual(
            partial_refund_tx.amount,
            -11.11,
            places=2,
            msg="The amount of the refund transaction should be the negative value of the amount "
                "to refund."
        )

    def test_partial_capture_transaction_values(self):
        self.provider.support_manual_capture = 'partial'
        self.provider.capture_manually = True
        tx = self._create_transaction('redirect', state='authorized')

        capture_tx = tx._create_child_transaction(11.11)
        self.assertEqual(
            capture_tx.reference,
            f'P-{tx.reference}',
            msg="The reference of a partial capture should be the prefixed reference of the source "
                "transaction.",
        )
        self.assertEqual(
            capture_tx.amount,
            11.11,
            msg="The amount of a partial capture should be the one passed as argument.",
        )
        self.assertEqual(
            capture_tx.currency_id,
            tx.currency_id,
            msg="The currency of the partial capture should be that of the source transaction.",
        )
        self.assertEqual(
            capture_tx.operation,
            tx.operation,
            msg="The operation of the partial capture should be the same as the source"
                " transaction.",
        )
        self.assertEqual(
            tx,
            capture_tx.source_transaction_id,
            msg="The partial capture transaction should be linked to the source transaction.",
        )
        self.assertEqual(
            capture_tx.partner_id,
            tx.partner_id,
            msg="The partner of the partial capture should be that of the source transaction.",
        )

    def test_compare_notification_data_throws(self):
        """ Test that `_compare_notification_data` throws if not overridden by the provider. """
        tx = self._create_transaction('redirect')
        with self.assertRaises(NotImplementedError):
            tx._compare_notification_data({})

    def test_capturing_child_tx_triggers_source_tx_state_update(self):
        self.provider.support_manual_capture = 'partial'
        self.provider.capture_manually = True
        source_tx = self._create_transaction(flow='direct', state='authorized')
        child_tx_1 = source_tx._create_child_transaction(100)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._update_source_transaction_state'
        ) as patched:
            child_tx_1._set_done()
            patched.assert_called_once()

    def test_voiding_child_tx_triggers_source_tx_state_update(self):
        self.provider.support_manual_capture = 'partial'
        self.provider.capture_manually = True
        source_tx = self._create_transaction(flow='direct', state='authorized')
        child_tx_1 = source_tx._create_child_transaction(100)
        child_tx_1._set_done()
        child_tx_2 = source_tx._create_child_transaction(source_tx.amount-100)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._update_source_transaction_state'
        ) as patched:
            child_tx_2._set_canceled()
            patched.assert_called_once()

    def test_capturing_partial_amount_leaves_source_tx_authorized(self):
        self.provider.support_manual_capture = 'partial'
        self.provider.capture_manually = True
        source_tx = self._create_transaction(flow='direct', state='authorized')
        child_tx_1 = source_tx._create_child_transaction(100)
        child_tx_1._set_done()
        self.assertEqual(
            source_tx.state,
            'authorized',
            msg="The whole amount of the source transaction has not been processed yet, it's state "
                "should still be 'authorized'.",
        )

    def test_capturing_full_amount_confirms_source_tx(self):
        self.provider.support_manual_capture = 'partial'
        self.provider.capture_manually = True
        source_tx = self._create_transaction(flow='direct', state='authorized')
        child_tx_1 = source_tx._create_child_transaction(100)
        child_tx_1._set_done()
        child_tx_2 = source_tx._create_child_transaction(source_tx.amount - 100)
        child_tx_2._set_canceled()
        self.assertEqual(
            source_tx.state,
            'done',
            msg="The whole amount of the source transaction has been processed, it's state is now "
                "'done'."
        )

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_update_state_to_illegal_target_state(self):
        tx = self._create_transaction('redirect', state='done')
        tx._update_state(['draft', 'pending', 'authorized'], 'cancel', None)
        self.assertEqual(tx.state, 'done')

    def test_update_state_to_extra_allowed_state(self):
        tx = self._create_transaction('redirect', state='done')
        tx._update_state(
            ['draft', 'pending', 'authorized', 'done'], 'cancel', None
        )
        self.assertEqual(tx.state, 'cancel')

    def test_updating_state_resets_post_processing_status(self):
        if self.account_payment_installed:
            self.skipTest("This test should not be run after account_payment is installed.")

        tx = self._create_transaction('redirect', state='draft')
        tx._set_pending()
        self.assertFalse(tx.is_post_processed)
        tx._post_process()
        self.assertTrue(tx.is_post_processed)

        tx._set_done()
        self.assertFalse(tx.is_post_processed)

    def test_log_processing_values(self):
        PaymentTransaction = self.env.registry['payment.transaction']
        tx = self._create_transaction('redirect', state='done', reference='TX-12345')
        secret_keys = {'provider_id': None}.keys()
        with (
            patch.object(PaymentTransaction, '_get_specific_secret_keys', lambda tx: secret_keys),
            self.assertLogs('odoo.addons.payment.models.payment_transaction') as cm,
        ):
            values = tx._get_processing_values()
            self.assertRegex(cm.output[0], r".reference.: .TX-12345.", "Values should be logged")
            self.assertNotRegex(cm.output[0], r"provider_id", "Secret keys should be hidden")
            self.assertEqual(values['provider_id'], tx.provider_id.id)

    def test_validate_amount_and_currency(self):
        amount = self.amount = 123.45
        currency = self.currency = self.env.ref('base.CHF')

        direct_tx = self._create_transaction('direct', state='done', reference='tx-direct')
        redirect_tx = self._create_transaction('redirect', reference='tx-redirect')
        refund_tx = direct_tx._create_child_transaction(amount, is_refund=True)

        for tx in (direct_tx, redirect_tx, refund_tx):
            tx._validate_amount_and_currency(amount, currency.name)
            with self.assertRaises(ValidationError):
                tx._validate_amount_and_currency(-amount, currency.name)
            with self.assertRaises(ValidationError):
                tx._validate_amount_and_currency(amount, 'EUR')

        # Special case 1: tolerate small rounding errors only
        epsilon = currency.rounding
        direct_tx._validate_amount_and_currency(amount + epsilon / 10, currency.name)
        with self.assertRaises(ValidationError):
            direct_tx._validate_amount_and_currency(amount + epsilon, currency.name)

        # Special case 2: don't validate validation transactions
        validation_tx = self._create_transaction(
            'redirect', operation='validation', amount=0, reference='tx-validation',
        )
        validation_tx._validate_amount_and_currency(None, None)
