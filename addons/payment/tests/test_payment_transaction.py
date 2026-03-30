# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentTransaction(PaymentCommon):

    def test_capture_allowed_for_authorized_users(self):
        """ Test that users who have access to a transaction can capture it. """
        if 'account' not in self.env["ir.module.module"]._installed():
            self.skipTest("account module is not installed")
        self.provider.support_manual_capture = True
        tx = self._create_transaction('redirect', state='authorized')
        user = self._prepare_user(self.internal_user, 'account.group_account_invoice')
        self._assert_does_not_raise(AccessError, tx.with_user(user).action_capture)

    def test_void_allowed_for_authorized_users(self):
        """ Test that users who have access to a transaction can void it. """
        if 'account' not in self.env["ir.module.module"]._installed():
            self.skipTest("account module is not installed")
        self.provider.support_manual_capture = True
        tx = self._create_transaction('redirect', state='authorized')
        user = self._prepare_user(self.internal_user, 'account.group_account_invoice')
        self._assert_does_not_raise(AccessError, tx.with_user(user).action_void)

    def test_refund_allowed_for_authorized_users(self):
        """ Test that users who have access to a transaction can refund it. """
        if 'account' not in self.env["ir.module.module"]._installed():
            self.skipTest("account module is not installed")
        self.provider.support_refund = 'full_only'
        tx = self._create_transaction('redirect', state='done')
        user = self._prepare_user(self.internal_user, 'account.group_account_invoice')
        self._assert_does_not_raise(AccessError, tx.with_user(user).action_refund)

    def test_capture_blocked_for_unauthorized_user(self):
        """ Test that users who don't have access to a transaction cannot capture it. """
        self.provider.support_manual_capture = True
        tx = self._create_transaction('redirect', state='authorized')
        self.assertRaises(AccessError, tx.with_user(self.internal_user).action_capture)

    def test_void_blocked_for_unauthorized_user(self):
        """ Test that users who don't have access to a transaction cannot void it. """
        self.provider.support_manual_capture = True
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
            )._reconcile_after_done()

        self.assertEqual(
            tx.refunds_count,
            1,
            msg="The refunds count should only consider transactions with operation 'refund'."
        )

    def test_refund_transaction_values(self):
        self.provider.support_refund = 'partial'
        tx = self._create_transaction('redirect', state='done')

        # Test the default values of a full refund transaction
        refund_tx = tx._create_refund_transaction()
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
            msg="The currency of the refund transaction should that of the source transaction."
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
            msg="The partner of the refund transaction should that of the source transaction."
        )

        # Test the values of a partial refund transaction with custom refund amount
        partial_refund_tx = tx._create_refund_transaction(amount_to_refund=11.11)
        self.assertAlmostEqual(
            partial_refund_tx.amount,
            -11.11,
            places=2,
            msg="The amount of the refund transaction should be the negative value of the amount "
                "to refund."
        )
