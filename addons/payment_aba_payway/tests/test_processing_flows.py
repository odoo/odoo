# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(AbaPaywayCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        """Test that returning from the checkout fetches the payment data and processes them."""
        tx = self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                "._send_api_request",
                return_value=self.check_transaction_response,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params={"tran_id": tx.reference})
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_redirect_notification_skips_check_if_webhook_notification_was_received(self):
        """Test that returning from the checkout doesn't check the transaction if the webhook
        notification was already received, whether it was processed or not."""
        processed_tx = self._create_transaction("redirect", reference="tx-processed", state="done")
        unprocessed_tx = self._create_transaction("redirect", reference="tx-unprocessed")
        unprocessed_tx._record(self.webhook_payment_data)
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        for tx in (processed_tx, unprocessed_tx):
            with (
                self.subTest(reference=tx.reference),
                patch(
                    "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                    "._send_api_request"
                ) as request_mock,
            ):
                self._make_http_get_request(url, params={"tran_id": tx.reference})
                self.assertEqual(request_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction("redirect")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("redirect")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock:
            self.opener.headers["X-PayWay-HMAC-SHA512"] = self.webhook_payment_data_signature
            self._make_json_request(url, data=self.webhook_payment_data)
            self.opener.headers.pop("X-PayWay-HMAC-SHA512")
        self.assertEqual(signature_check_mock.call_args[0][0], self.webhook_payment_data_signature)
