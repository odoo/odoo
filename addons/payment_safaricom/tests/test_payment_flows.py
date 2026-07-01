# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment_safaricom import const
from odoo.addons.payment_safaricom.tests.common import SafaricomCommon


@tagged("post_install", "-at_install")
class TestPaymentFlows(SafaricomCommon):
    @mute_logger("odoo.addons.payment_safaricom.controllers.main")
    def test_payment_initiation_triggers_stk_push(self):
        """Test that submitting the inline payment form triggers an STK Push API request."""
        tx = self._create_transaction("direct")
        url = self._build_url(const.PAYMENT_URL)
        with self._mock_send_api_request({
            "ResponseCode": "0",
            "CheckoutRequestID": self.checkout_id,
        }) as mock_request:
            self.make_jsonrpc_request(url, self._get_stk_push_params(tx))
        self.assertEqual(mock_request.call_count, 1)

    @mute_logger("odoo.addons.payment_safaricom.controllers.main", "odoo.http")
    def test_payment_initiation_rejects_invalid_access_token(self):
        """Test that the STK Push endpoint rejects requests with a forged access token."""
        tx = self._create_transaction("direct")
        url = self._build_url(const.PAYMENT_URL)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(url, self._get_stk_push_params(tx, access_token="forged"))

    @mute_logger("odoo.addons.payment_safaricom.controllers.main", "odoo.http")
    def test_payment_initiation_rejects_already_processed_transaction(self):
        """Test that the STK Push endpoint rejects transactions that are no longer draft."""
        tx = self._create_transaction("direct", state="pending")
        url = self._build_url(const.PAYMENT_URL)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(url, self._get_stk_push_params(tx))

    @mute_logger("odoo.addons.payment_safaricom.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        tx = self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_URL)
        with (
            patch(
                "odoo.addons.payment_safaricom.controllers.main.verify_hash_signed",
                return_value={"reference": tx.reference},
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(
                url + "?reference=" + self.reference, data=self.webhook_payment_data
            )
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_safaricom.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        """Test that the webhook handler verifies the signature before processing."""
        tx = self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_URL)
        with (
            patch(
                "odoo.addons.payment_safaricom.controllers.main.verify_hash_signed",
                return_value={"reference": tx.reference},
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"),
        ):
            self._make_json_request(
                url + "?reference=" + self.reference, data=self.webhook_payment_data
            )
        self.assertEqual(signature_check_mock.call_args[0][2], self.reference)

    @mute_logger("odoo.addons.payment_safaricom.controllers.main", "odoo.http")
    def test_webhook_rejects_malformed_signed_reference(self):
        """Test that a signed reference that can't be decoded is rejected with a 403 instead of
        crashing the webhook."""
        url = self._build_url(const.WEBHOOK_URL)
        response = self._make_json_request(url + "?reference=dummy", data=self.webhook_payment_data)
        self.assertEqual(response.status_code, 403)

    def test_status_page_renders_safaricom_template(self):
        """Test that the payment status page is rendered with the Safaricom template for
        Safaricom transactions."""
        tx = self._create_transaction("direct", state="pending")
        with patch(
            "odoo.addons.payment.controllers.payment_status.PaymentStatus"
            "._get_monitored_transaction",
            return_value=tx,
        ):
            response = self.url_open("/payment/status")
        self.assertIn("o_safaricom_cancel", response.text)

    @mute_logger("odoo.http")
    def test_cancel_rejects_session_without_monitored_transaction(self):
        """Test that the cancel endpoint rejects requests when no monitored transaction is found
        in the session."""
        url = self._build_url(const.CANCEL_URL)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(url, {})

    def test_cancel_records_cancellation_payload(self):
        """Test that the cancel endpoint records a cancellation payload for the monitored pending
        transaction."""
        tx = self._create_transaction("direct", state="pending")
        url = self._build_url(const.CANCEL_URL)
        with (
            patch(
                "odoo.addons.payment.controllers.payment_status.PaymentStatus"
                "._get_monitored_transaction",
                return_value=tx,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._run_processing"
            ),
        ):
            self.make_jsonrpc_request(url, {})
        self.assertEqual(record_mock.call_count, 1)

    def test_cancel_skips_transaction_in_final_state(self):
        """Test that the cancel endpoint does not record a cancellation payload when the
        monitored transaction has already reached a final state."""
        tx = self._create_transaction("direct", state="done")
        url = self._build_url(const.CANCEL_URL)
        with (
            patch(
                "odoo.addons.payment.controllers.payment_status.PaymentStatus"
                "._get_monitored_transaction",
                return_value=tx,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self.make_jsonrpc_request(url, {})
        self.assertEqual(record_mock.call_count, 0)
