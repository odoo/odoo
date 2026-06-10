# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_ecpay import const
from odoo.addons.payment_ecpay.tests.common import EcpayCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(EcpayCommon, PaymentHttpCommon):
    def test_compute_signature_returns_correct_signature(self):
        signature = self.provider._ecpay_calculate_signature(self.payment_result_data)
        self.assertEqual(signature, self.webhook_payment_data_signature)

    def test_compute_signature_without_language_returns_correct_signature(self):
        self.env["res.lang"]._activate_lang("zh_TW")
        tx = self._create_transaction(
            "redirect", payment_method_id=self.env.ref("payment.payment_method_card").id
        )
        rendering_values = tx.with_context(lang="zh_TW")._get_specific_rendering_values(None)
        signature_data = dict(rendering_values)
        signature_data.pop("CheckMacValue", None)
        signature_data.pop("api_url", None)
        expected_mac = tx.provider_id._ecpay_calculate_signature(signature_data)
        self.assertEqual(rendering_values["CheckMacValue"], expected_mac)

    @mute_logger("odoo.addons.payment_ecpay.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        """Test that receiving a valid redirect notification triggers the processing of the
        payment data."""
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_result_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_ecpay.controllers.main")
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
            self._make_http_post_request(url, data=self.payment_result_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_ecpay.controllers.main")
    def test_webhook_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("redirect")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.payment_result_data)
        self.assertEqual(signature_check_mock.call_count, 1)
