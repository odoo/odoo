# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_razorpay.controllers.main import RazorpayController
from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(RazorpayCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_razorpay.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        self._create_transaction("direct")
        url = self._build_url(RazorpayController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider"
                "._razorpay_calculate_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.redirect_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_razorpay.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction("direct")
        url = self._build_url(RazorpayController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider"
                "._razorpay_calculate_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_razorpay.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(RazorpayController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider"
                "._razorpay_calculate_signature"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.redirect_payment_data)
            self.assertEqual(
                signature_check_mock.call_args[0][0], self.redirect_payment_data_signature
            )

    @mute_logger("odoo.addons.payment_razorpay.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(RazorpayController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_razorpay.models.payment_provider.PaymentProvider"
                "._razorpay_calculate_signature"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self.opener.headers["X-Razorpay-Signature"] = self.webhook_payment_data_signature
            self._make_json_request(url, data=self.webhook_payment_data)
            self.opener.headers.pop("X-Razorpay-Signature")

            self.assertEqual(
                signature_check_mock.call_args[0][0], self.webhook_payment_data_signature
            )

    def test_redirect_compute_signature_returns_correct_signature(self):
        signature = self.provider._razorpay_calculate_signature(
            self.redirect_payment_data, is_redirect=True
        )
        self.assertEqual(signature, self.redirect_payment_data_signature)

    def test_webhook_compute_signature_returns_correct_signature(self):
        signature = self.provider._razorpay_calculate_signature(
            json.dumps(self.webhook_payment_data).encode(), is_redirect=False
        )
        self.assertEqual(signature, self.webhook_payment_data_signature)
