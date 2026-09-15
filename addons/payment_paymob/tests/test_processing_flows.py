# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import urlencode

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PaymobCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_normalize_webhook_data(self):
        normalized_data = PaymobController._normalize_response(
            self.webhook_data["obj"], self.hmac_signature
        )
        self.assertDictEqual(normalized_data, self.redirection_data)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._return_url)
        with (
            patch("odoo.addons.payment_paymob.controllers.main.PaymobController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_get_request(url, params=self.redirection_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._webhook_url)
        with (
            patch("odoo.addons.payment_paymob.controllers.main.PaymobController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.webhook_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._return_url)
        with (
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._verify_signature"
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_get_request(url, params=self.redirection_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect", provider_reference=self.order_id)
        url = self._build_url(PaymobController._webhook_url)
        with (
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._verify_signature"
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_json_request(url, data=self.webhook_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_reject_notification_with_incorrect_payload(self):
        tx = self._create_transaction("redirect", provider_reference=self.order_id)
        query_string = urlencode({"hmac": self.hmac_signature})
        url = f"{self._build_url(PaymobController._webhook_url)}?{query_string}"
        with (
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._verify_signature"
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_json_request(url, data=self.webhook_data)
            signature_check_mock.assert_called_once_with(self.redirection_data, tx)

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

    def test_accept_notification_with_valid_signature(self):
        tx = self._create_transaction("redirect")
        self._assert_does_not_raise(
            Forbidden, PaymobController._verify_signature, tx, self.webhook_data
        )

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_reject_notification_with_missing_signature(self):
        tx = self._create_transaction("redirect")
        payload = dict(self.webhook_data, hmac=None)
        self.assertRaises(Forbidden, PaymobController._verify_signature, payload, tx)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_reject_notification_with_invalid_signature(self):
        tx = self._create_transaction("redirect")
        payload = dict(self.webhook_data, hmac="dummy")
        self.assertRaises(Forbidden, PaymobController._verify_signature, payload, tx)
