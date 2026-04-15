# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PaymobCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(PaymobController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_get_request(url, params=self.redirection_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(PaymobController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(
                url, data={"obj": self.webhook_data, "hmac": self.hmac_signature}
            )
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(PaymobController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_get_request(url, params=self.redirection_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.hmac_signature)

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(PaymobController._webhook_url) + f"?hmac={self.hmac_signature}"
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_paymob.controllers.main.PaymobController._compute_signature"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_json_request(url, data={"obj": self.webhook_data})
            self.assertEqual(signature_check_mock.call_args[0][0], self.hmac_signature)

    def test_normalize_response_returns_correct_response(self):
        normalized_data = PaymobController._normalize_response(
            self.webhook_data, self.hmac_signature
        )
        self.assertDictEqual(normalized_data, self.redirection_data)

    def test_compute_signature_returns_correct_signature(self):
        hmac_key = self.provider.paymob_hmac_key
        signature = PaymobController._compute_signature(self.redirection_data, hmac_key)
        self.assertEqual(signature, self.hmac_signature)
