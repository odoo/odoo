# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestIrWebsocket(PaymentCommon):
    def setUp(self):
        super().setUp()
        self.tx = self._create_transaction("redirect")
        access_token = self._generate_test_access_token(self.tx.id)
        self.channel = f"payment_transaction_channel:{self.tx.id},{access_token}"

        self.IrWebsocket = self.env["ir.websocket"]
        self.PaymentTransaction = self.registry["payment.transaction"]

    def test_valid_channel_resolves_to_transaction(self):
        tx = self.IrWebsocket._get_transaction_from_channel(self.channel)
        self.assertEqual(tx, self.tx)

    def test_channel_with_invalid_token_is_rejected(self):
        channel = f"payment_transaction_channel:{self.tx.id},invalid-token"
        tx = self.IrWebsocket._get_transaction_from_channel(channel)
        self.assertFalse(tx)

    def test_channel_with_unknown_transaction_is_rejected(self):
        access_token = self._generate_test_access_token(0)
        channel = f"payment_transaction_channel:0,{access_token}"
        tx = self.IrWebsocket._get_transaction_from_channel(channel)
        self.assertFalse(tx)

    def test_subscription_resends_status_notifications(self):
        self._update_transaction(self.tx, is_post_processed=True)
        with (
            patch("odoo.addons.mail.models.ir_websocket.IrWebsocket._subscribe"),
            patch.object(
                self.PaymentTransaction, "_notify_status", autospec=True
            ) as notify_status_mock,
        ):
            self.IrWebsocket._subscribe({"channels": [self.channel]})
        self.assertEqual(notify_status_mock.call_args.args[0], self.tx)

    def test_subscription_skips_not_yet_post_processed_transactions(self):
        self._update_transaction(self.tx, is_post_processed=False)
        with (
            patch("odoo.addons.mail.models.ir_websocket.IrWebsocket._subscribe"),
            patch.object(
                self.PaymentTransaction, "_notify_status", autospec=True
            ) as notify_status_mock,
        ):
            self.IrWebsocket._subscribe({"channels": [self.channel]})
        self.assertEqual(notify_status_mock.call_count, 0)

    def test_subscription_skips_status_notification_for_invalid_channels(self):
        channel = f"payment_transaction_channel:{self.tx.id},invalid-token"
        with (
            patch("odoo.addons.mail.models.ir_websocket.IrWebsocket._subscribe"),
            patch.object(self.PaymentTransaction, "_notify_status") as notify_status_mock,
        ):
            self.IrWebsocket._subscribe({"channels": [channel]})
        self.assertEqual(notify_status_mock.call_count, 0)
