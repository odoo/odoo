# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from werkzeug.exceptions import Forbidden

from odoo.tests import freeze_time, tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(StripeCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_stripe.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(StripeController._return_url)
        with (
            self._mock_send_api_request(new=self._mock_setup_intent_request),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params={"reference": self.reference})
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_stripe.controllers.main")
    def test_return_from_tokenization_request(self):
        tx = self._create_transaction("direct", amount=0, operation="validation", tokenize=True)
        url = self._build_url(StripeController._return_url)
        with (
            patch.object(StripeController, "_verify_signature"),
            self._mock_send_api_request(new=self._mock_setup_intent_request),
        ):
            res = self._make_http_get_request(url, params={"reference": tx.reference})
            self.assertTrue(res.ok, msg=res.content.decode())

    @mute_logger("odoo.addons.payment_stripe.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(StripeController._webhook_url)
        with (
            patch("odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_stripe.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(StripeController._webhook_url)
        with patch(
            "odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature"
        ) as signature_check_mock:
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger(
        "odoo.addons.payment_stripe.controllers.main",
        "odoo.addons.payment_stripe.models.payment_transaction",
    )
    def test_canceled_refund_webhook_notification_triggers_processing(self):
        """Test that receiving a webhook notification for a refund cancellation
        (`charge.refund.updated` event) triggers the processing of the payment data."""
        source_tx = self._create_transaction("redirect", state="done")
        source_tx._create_child_transaction(
            source_tx.amount, is_refund=True, provider_reference=self.refund_object["id"]
        )
        url = self._build_url(StripeController._webhook_url)
        with (
            patch("odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.canceled_refund_payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger(
        "odoo.addons.payment_stripe.controllers.main",
        "odoo.addons.payment_stripe.models.payment_transaction",
    )
    def test_refund_webhook_notification_matches_refund_of_capture_child(self):
        """Test that refund webhooks match refunds created from capture transactions."""
        source_tx = self._create_transaction("direct", state="done")
        capture_tx = source_tx._create_child_transaction(
            source_tx.amount, state="done", provider_reference="pi_capture"
        )
        refund_tx = capture_tx._create_child_transaction(
            capture_tx.amount,
            is_refund=True,
            state="done",
            provider_reference=self.refund_object["id"],
        )
        url = self._build_url(StripeController._webhook_url)
        payload = dict(self.refund_payment_data)
        payload["data"] = dict(payload["data"])
        payload["data"]["object"] = dict(payload["data"]["object"], captured=True)
        with patch(
            "odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature"
        ), patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
        ) as process_mock:
            self._make_json_request(url, data=payload)
        refund_txs = self.env["payment.transaction"].search([
            ("operation", "=", "refund"),
            ("source_transaction_id", "in", (source_tx | capture_tx).ids),
        ])
        self.assertEqual(process_mock.call_count, 0)
        self.assertEqual(refund_txs, refund_tx)

    @mute_logger(
        "odoo.addons.payment_stripe.controllers.main",
        "odoo.addons.payment_stripe.models.payment_transaction",
    )
    def test_void_webhook_notification_does_not_trigger_processing(self):
        """Test that receiving a webhook notification for a voided authorization does not trigger
        the processing of the payment data."""
        self.provider.capture_manually = True
        tx = self._create_transaction("direct", state="authorized")
        url = self._build_url(StripeController._webhook_url)
        with (
            patch("odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.void_payment_data)
        self.assertEqual(record_mock.call_count, 0)
        self.assertFalse(tx.child_transaction_ids)

    @mute_logger("odoo.addons.payment_stripe.controllers.main")
    @mute_logger("odoo.addons.payment_stripe.models.payment_transaction")
    def test_webhook_notification_skips_signature_verification_for_missing_transactions(self):
        url = self._build_url(StripeController._webhook_url)
        payload = copy.deepcopy(self.payment_data)
        payload["data"]["object"]["description"] = None
        with patch(
            "odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature"
        ) as signature_check_mock:
            self._make_json_request(url, data=payload)
            self.assertEqual(signature_check_mock.call_count, 0)

    @freeze_time("2026-02-13 15:08:21")
    def test_accept_notification_with_valid_signature(self):
        tx = self._create_transaction("redirect")
        timestamp = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        signature_data = {
            "v1": "784393e05d0740e61283ff81eb3738b3355a67e031bf465e92ebd0f424478a26",
            "t": timestamp,
        }
        signature_header = ",".join(f"{k}={v}" for k, v in signature_data.items())
        mock_request = MagicMock()
        mock_request.httprequest.data = b""
        mock_request.httprequest.headers = {"Stripe-Signature": signature_header}
        controller = StripeController()
        with patch("odoo.addons.payment_stripe.controllers.main.request", new=mock_request):
            self._assert_does_not_raise(Forbidden, controller._verify_signature, tx)

    @mute_logger("odoo.addons.payment_stripe.controllers.main")
    def test_reject_notification_when_missing_secret(self):
        self.stripe.stripe_webhook_secret = False
        tx = self._create_transaction("redirect")
        controller = StripeController()
        self.assertRaises(Forbidden, controller._verify_signature, tx)

    @mute_logger("odoo.addons.payment_stripe.controllers.main", "odoo.addons.payment.utils")
    def test_reject_notification_with_missing_timestamp(self):
        tx = self._create_transaction("redirect")
        signature_header = "v1=Test_Signature"
        mock_request = MagicMock()
        mock_request.httprequest.data = b""
        mock_request.httprequest.headers = {"Stripe-Signature": signature_header}
        controller = StripeController()
        with patch("odoo.addons.payment_stripe.controllers.main.request", new=mock_request):
            self.assertRaises(Forbidden, controller._verify_signature, tx)

    @freeze_time("2026-02-13 15:08:21")
    @mute_logger("odoo.addons.payment_stripe.controllers.main", "odoo.addons.payment.utils")
    def test_reject_notification_with_missing_signature(self):
        tx = self._create_transaction("redirect")
        timestamp = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        signature_data = {"t": timestamp}
        signature_header = ",".join(f"{k}={v}" for k, v in signature_data.items())
        mock_request = MagicMock()
        mock_request.httprequest.data = b""
        mock_request.httprequest.headers = {"Stripe-Signature": signature_header}
        controller = StripeController()
        with patch("odoo.addons.payment_stripe.controllers.main.request", new=mock_request):
            self.assertRaises(Forbidden, controller._verify_signature, tx)

    @freeze_time("2026-02-13 15:08:21")
    @mute_logger("odoo.addons.payment_stripe.controllers.main", "odoo.addons.payment.utils")
    def test_reject_notification_with_invalid_signature(self):
        tx = self._create_transaction("redirect")
        timestamp = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        signature_data = {"v1": "Wrong", "t": timestamp}
        signature_header = ",".join(f"{k}={v}" for k, v in signature_data.items())
        mock_request = MagicMock()
        mock_request.httprequest.data = b""
        mock_request.httprequest.headers = {"Stripe-Signature": signature_header}
        controller = StripeController()
        with patch("odoo.addons.payment_stripe.controllers.main.request", new=mock_request):
            self.assertRaises(Forbidden, controller._verify_signature, tx)

    @freeze_time("2026-02-13 15:08:21")
    @mute_logger("odoo.addons.payment_stripe.controllers.main", "odoo.addons.payment.utils")
    def test_reject_notification_with_outdated_signature(self):
        tx = self._create_transaction("redirect")
        timestamp = int(
            (datetime.now(UTC) - timedelta(minutes=1)).timestamp()
            - StripeController.WEBHOOK_AGE_TOLERANCE
        )
        signature_data = {"v1": "Test Signature", "t": timestamp}
        signature_header = ",".join(f"{k}={v}" for k, v in signature_data.items())
        mock_request = MagicMock()
        mock_request.httprequest.data = b""
        mock_request.httprequest.headers = {"Stripe-Signature": signature_header}
        controller = StripeController()
        with patch("odoo.addons.payment_stripe.controllers.main.request", new=mock_request):
            self.assertRaises(Forbidden, controller._verify_signature, tx)
