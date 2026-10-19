# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PaymobCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params=self.redirection_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.webhook_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
        ):
            self._make_http_get_request(url, params=self.redirection_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.hmac_signature)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._webhook_url) + f"?hmac={self.hmac_signature}"
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
        ):
            self._make_json_request(url, data=self.webhook_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.hmac_signature)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_reject_notification_with_incorrect_payload(self):
        tx = self._create_transaction("redirect", provider_reference=self.order_id)
        query_string = urlencode({"hmac": self.hmac_signature})
        url = f"{self._build_url(PaymobController._webhook_url)}?{query_string}"
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ) as signature_computation_mock,
        ):
            self._make_json_request(url, data=self.webhook_data)
            signature_computation_mock.assert_called_once_with(
                self.redirection_data, tx.provider_id.paymob_hmac_key
            )

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_reject_redirect_notification_with_incorrect_provider_reference(self):
        self._create_transaction("redirect", provider_reference="dummy")
        url = self._build_url(PaymobController._return_url)
        response = self._make_http_get_request(url, params=self.redirection_data)
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_reject_webhook_notification_with_incorrect_provider_reference(self):
        self._create_transaction("redirect", provider_reference="dummy")
        query_string = urlencode({"hmac": self.hmac_signature})
        url = f"{self._build_url(PaymobController._webhook_url)}?{query_string}"
        response = self._make_json_request(url, data=self.webhook_data)
        self.assertEqual(response.status_code, 403)

    def test_normalize_response_returns_correct_response(self):
        normalized_data = PaymobController._normalize_response(
            self.webhook_data["obj"], self.hmac_signature
        )
        self.assertDictEqual(normalized_data, self.redirection_data)

    def test_compute_signature_returns_correct_signature(self):
        hmac_key = self.provider.paymob_hmac_key
        signature = PaymobController._compute_signature(self.redirection_data, hmac_key)
        self.assertEqual(signature, self.hmac_signature)
