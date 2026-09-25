# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from odoo.exceptions import ValidationError
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
            self._make_json_request(url, data=self.webhook_notification_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_xendit.controllers.main")
    def test_webhook_notification_unwraps_envelope(self):
        """Test that webhook notifications wrapped in an `event` envelope are unwrapped before
        being recorded for processing."""
        self._create_transaction("redirect")
        url = self._build_url(XenditController._webhook_url)
        envelope = {"event": "payment_session.completed", "data": self.webhook_notification_data}
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=envelope)
        self.assertEqual(record_mock.call_count, 1)
        self.assertEqual(record_mock.call_args.args[0], self.webhook_notification_data)

    @mute_logger("odoo.addons.payment_xendit.controllers.main")
    def test_webhook_notification_tokenizes_on_activation_event(self):
        """Test that a `payment_token.activation` webhook notification tokenizes the
        transaction directly, bypassing the generic payment data processing."""
        tx = self._create_transaction("redirect", tokenize=True)
        url = self._build_url(XenditController._webhook_url)
        envelope = {
            "event": "payment_token.activation",
            "data": self.token_activation_notification_data,
        }
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._tokenize"
            ) as tokenize_mock,
        ):
            self._make_json_request(url, data=envelope)
            self._run_processing()
        self.assertEqual(tokenize_mock.call_count, 1)
        self.assertEqual(tokenize_mock.call_args.args[0], self.token_activation_notification_data)
        self.assertEqual(tx.state, "draft", "The token status shouldn't update the tx state")
        self.assertFalse(tx.payment_data_ids, "The activation event should have been processed")

    @mute_logger("odoo.addons.payment_xendit.controllers.main")
    def test_webhook_notification_skips_activation_event_without_tokenize(self):
        """Test that a `payment_token.activation` webhook notification is ignored for a
        transaction that doesn't request tokenization."""
        tx = self._create_transaction("redirect")  # tokenize defaults to False
        url = self._build_url(XenditController._webhook_url)
        envelope = {
            "event": "payment_token.activation",
            "data": self.token_activation_notification_data,
        }
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._tokenize"
            ) as tokenize_mock,
        ):
            self._make_json_request(url, data=envelope)
            self._run_processing()
        self.assertEqual(tokenize_mock.call_count, 0)
        self.assertEqual(tx.state, "draft")

    @mute_logger("odoo.addons.payment_xendit.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("redirect")
        url = self._build_url(XenditController._webhook_url)
        with patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock:
            self.opener.headers["x-callback-token"] = self.provider.xendit_webhook_token
            self._make_json_request(url, data=self.webhook_notification_data)
            self.opener.headers.pop("x-callback-token")

            self.assertEqual(
                signature_check_mock.call_args[0][0], self.provider.xendit_webhook_token
            )

    def test_set_xendit_transactions_to_pending_on_return(self):
        def build_return_url(**kwargs):
            url_params = url_encode(dict(kwargs, tx_ref=self.reference))
            return self._build_url(f"{XenditController._return_url}?{url_params}")

        self.reference = "xendit_tx1"
        tx = self._create_transaction("redirect")

        with patch.object(payment_utils, "generate_access_token", self._generate_test_access_token):
            token = payment_utils.generate_access_token(tx.reference, tx.amount)

            self._make_http_get_request(build_return_url(success="true", access_token="coincoin"))
            self._run_processing()
            self.assertEqual(tx.state, "draft", "Random GET requests shouldn't affect tx state")

            self._make_http_get_request(build_return_url(success="false", access_token=token))
            self._run_processing()
            self.assertEqual(tx.state, "draft", "Failure returns shouldn't change tx state")

            self._make_http_get_request(build_return_url(success="true", access_token=token))
            self._run_processing()
            self.assertEqual(tx.state, "pending", "Successful returns should set state to pending")

    def test_return_syncs_status_from_provider_when_reference_known(self):
        """Test that a successful return checks the session status with Xendit rather than
        blindly setting the transaction to pending, when the session id is already known."""
        self.reference = "xendit_tx2"
        tx = self._create_transaction("redirect", provider_reference="ps-64a8f9c614802d6c402cd82d")

        with patch.object(payment_utils, "generate_access_token", self._generate_test_access_token):
            token = payment_utils.generate_access_token(tx.reference, tx.amount)
            url_params = url_encode({
                "tx_ref": tx.reference,
                "success": "true",
                "access_token": token,
            })
            url = self._build_url(f"{XenditController._return_url}?{url_params}")

            with patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                "._send_api_request",
                return_value=self.webhook_notification_data,
            ) as make_request_mock:
                self._make_http_get_request(url)
        self._run_processing()

        make_request_mock.assert_called_once_with("GET", f"sessions/{tx.provider_reference}")
        self.assertEqual(
            tx.state, "done", "A completed session status should confirm the transaction directly"
        )

    @mute_logger("odoo.addons.payment_xendit.models.payment_transaction")
    def test_return_falls_back_to_pending_when_sync_fails(self):
        """Test that a successful return still sets the transaction to pending if the status
        check with Xendit fails, instead of leaving it stuck in draft."""
        self.reference = "xendit_tx3"
        tx = self._create_transaction("redirect", provider_reference="ps-64a8f9c614802d6c402cd82d")

        with patch.object(payment_utils, "generate_access_token", self._generate_test_access_token):
            token = payment_utils.generate_access_token(tx.reference, tx.amount)
            url_params = url_encode({
                "tx_ref": tx.reference,
                "success": "true",
                "access_token": token,
            })
            url = self._build_url(f"{XenditController._return_url}?{url_params}")

            with patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                "._send_api_request",
                side_effect=ValidationError("Xendit: nope"),
            ):
                self._make_http_get_request(url)
        self._run_processing()

        self.assertEqual(tx.state, "pending")

    def test_return_confirms_pending_token_payment_after_3ds_challenge(self):
        """Test that returning from a 3DS authentication challenge for a token payment - already
        `pending` by charge time, unlike a checkout redirect which stays `draft` - is checked
        against Xendit and confirmed directly."""
        self.reference = "xendit_tx5"
        tx = self._create_transaction(
            "token", provider_reference="pr-64a8d9c614802d6c402cd82d", state="pending"
        )

        with patch.object(payment_utils, "generate_access_token", self._generate_test_access_token):
            token = payment_utils.generate_access_token(tx.reference, tx.amount)
            url_params = url_encode({
                "tx_ref": tx.reference,
                "success": "true",
                "access_token": token,
            })
            url = self._build_url(f"{XenditController._return_url}?{url_params}")

            with patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                "._send_api_request",
                return_value=self.payment_request_notification_data,
            ) as make_request_mock:
                self._make_http_get_request(url)
        self._run_processing()

        make_request_mock.assert_called_once_with(
            "GET",
            f"v3/payment_requests/{tx.provider_reference}",
            api_version="2024-11-11",
        )
        self.assertEqual(tx.state, "done")
