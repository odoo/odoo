# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.controllers.main import XenditController
from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(XenditCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_xendit.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification and signature verified triggers the
        processing of the payment data."""
        self._create_transaction("redirect")
        url = self._build_url(XenditController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_xendit.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("redirect")
        url = self._build_url(XenditController._webhook_url)
        with patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock:
            self.opener.headers["x-callback-token"] = self.provider.xendit_webhook_token
            self._make_json_request(url, data=self.webhook_payment_data)
            self.opener.headers.pop("x-callback-token")

            self.assertEqual(
                signature_check_mock.call_args[0][0], self.provider.xendit_webhook_token
            )

    def _build_return_url(self, tx_ref, **kwargs):
        url_params = url_encode(dict(kwargs, tx_ref=tx_ref))
        return self._build_url(f"{XenditController._return_url}?{url_params}")

    def test_returning_from_payment_triggers_processing(self):
        """Test that returning from a successful payment with a valid access token triggers the
        processing of the payment data."""
        tx = self._create_transaction("redirect")
        with (
            patch("odoo.addons.payment.utils.check_access_token", return_value=True),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(
                self._build_return_url(tx.reference, success="true", access_token="dummy")
            )
        self.assertEqual(record_mock.call_count, 1)

    def test_returning_from_payment_triggers_signature_check(self):
        """Test that returning from a successful payment triggers an access token check."""
        tx = self._create_transaction("redirect")
        with patch("odoo.addons.payment.utils.check_access_token") as signature_check_mock:
            self._make_http_get_request(
                self._build_return_url(tx.reference, success="true", access_token="dummy")
            )
        self.assertEqual(signature_check_mock.call_args[0][0], "dummy")

    def test_return_with_invalid_access_token_does_not_trigger_processing(self):
        """Test that a return request with an access token that doesn't match the transaction
        doesn't affect the transaction state."""
        tx = self._create_transaction("redirect")
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(
                self._build_return_url(tx.reference, success="true", access_token="coincoin")
            )
        self.assertEqual(record_mock.call_count, 0)

    def test_return_with_failed_payment_does_not_trigger_processing(self):
        """Test that a return request indicating a failed payment doesn't affect the transaction
        state."""
        tx = self._create_transaction("redirect")
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(
                self._build_return_url(tx.reference, success="false", access_token="dummy")
            )
        self.assertEqual(record_mock.call_count, 0)

    def test_set_xendit_transactions_to_pending_on_return(self):
        """Test that a valid return request with a successful payment sets the transaction to
        pending."""
        tx = self._create_transaction("redirect")
        with patch.object(payment_utils, "generate_access_token", self._generate_test_access_token):
            token = payment_utils.generate_access_token(tx.reference, tx.amount)

        self._make_http_get_request(
            self._build_return_url(tx.reference, success="true", access_token=token)
        )
        payment_data = self.env["payment.data"].search([("transaction_id", "=", tx.id)])
        self.assertEqual(payment_data.payload["status"], "PENDING")
