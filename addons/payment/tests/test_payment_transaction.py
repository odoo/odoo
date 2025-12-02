# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentCommon):

    def test_is_live_when_created_by_enabled_provider(self):
        self.provider.state = 'enabled'
        tx = self._create_transaction('redirect')
        self.assertTrue(tx.is_live)

    def test_is_not_live_when_created_by_test_provider(self):
        self.provider.state = 'test'  # Will work with anything other than 'enabled'
        tx = self._create_transaction('redirect')
        self.assertFalse(tx.is_live)

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

    def test_capturing_tx_creates_child_tx(self):
        """Test that capturing a transaction creates a child capture transaction."""
        self.provider.capture_manually = True
        self.provider.support_manual_capture = 'partial'
        source_tx = self._create_transaction('direct', state='authorized')
        child_tx = source_tx._capture()
        self.assertTrue(child_tx)
        self.assertNotEqual(child_tx, source_tx)

    def test_voiding_tx_creates_child_tx(self):
        """Test that voiding a transaction creates a child void transaction."""
        self.provider.capture_manually = True
        self.provider.support_manual_capture = 'partial'
        source_tx = self._create_transaction('direct', state='authorized')
        child_tx = source_tx._void()
        self.assertTrue(child_tx)
        self.assertNotEqual(child_tx, source_tx)

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

    def test_validate_amount_skips_validation_transactions(self):
        """Test that the amount validation is skipped for validation transactions."""
        tx = self._create_transaction('redirect', operation='validation')
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._extract_amount_data', return_value={'amount': None, 'currency_code': None},
        ):
            tx._validate_amount({})
        self.assertNotEqual(tx.state, 'error')

    def test_processing_does_not_apply_updates_when_amount_data_is_invalid(self):
        tx = self._create_transaction('redirect', state='draft', amount=100)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._extract_amount_data', return_value={'amount': 10, 'currency_code': 'USD'}
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._apply_updates'
        ) as apply_updates_mock:
            tx._process('test', {})
        self.assertEqual(tx.state, 'error')
        self.assertEqual(apply_updates_mock.call_count, 0)

    def test_processing_tokenizes_validated_transaction(self):
        """Test that `_process` tokenizes 'authorized' and 'done' transactions when possible."""
        self.provider.support_manual_capture = 'partial'
        self.provider.capture_manually = True
        for state in ['authorized', 'done']:
            tx = self._create_transaction(
                'redirect', reference=f'Test {state}', state=state, tokenize=True
            )
            with patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
                '._validate_amount', return_value=None
            ), patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
                '._extract_token_values', return_value={'provider_ref': 'test'}
            ):
                tx._process('test', {})
            self.assertTrue(tx.token_id)

    def test_processing_only_tokenizes_when_requested(self):
        """Test that `_process` only triggers tokenization if the user requested it."""
        tx = self._create_transaction('redirect', state='done', tokenize=False)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._validate_amount', return_value=None
        ), patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._tokenize'
        ) as tokenize_mock:
            tx._process('test', {})
        self.assertEqual(tokenize_mock.call_count, 0)

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
