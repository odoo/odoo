# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_flutterwave.controllers.main import FlutterwaveController
from odoo.addons.payment_flutterwave.tests.common import FlutterwaveCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(FlutterwaveCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_flutterwave.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the notification
        data."""
        self._create_transaction(flow="redirect")
        url = self._build_url(FlutterwaveController._return_url)
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=self.verification_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_get_request(url, params=self.redirect_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_flutterwave.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction("redirect")
        url = self._build_url(FlutterwaveController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_flutterwave.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction(flow="redirect")
        url = self._build_url(FlutterwaveController._return_url)
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=self.verification_data,
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_get_request(url, params=self.redirect_payment_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_flutterwave.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(FlutterwaveController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self.opener.headers["verif-hash"] = self.provider.flutterwave_webhook_secret
            self._make_json_request(url, data=self.webhook_payment_data)
            self.opener.headers.pop("verif-hash")

            self.assertEqual(
                signature_check_mock.call_args[0][0], self.provider.flutterwave_webhook_secret
            )
