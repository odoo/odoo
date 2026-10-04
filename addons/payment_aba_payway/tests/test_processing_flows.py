# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(AbaPaywayCommon, PaymentHttpCommon):
    def _make_signed_json_request(self, url, data, signature):
        """Make a JSON request to the provided URL with the signature in the headers.

        :param str url: The URL to make the request to.
        :param dict data: The data to be sent in the request body in JSON format.
        :param str signature: The signature of the data.
        :return: The response of the request.
        :rtype: requests.models.Response
        """
        self.opener.headers["X-PayWay-HMAC-SHA512"] = signature
        try:
            return self._make_json_request(url, data=data)
        finally:
            self.opener.headers.pop("X-PayWay-HMAC-SHA512")

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record",
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock:
            self._make_signed_json_request(
                url, self.webhook_payment_data, self.webhook_payment_data_signature,
            )
        self.assertEqual(signature_check_mock.call_args[0][0], self.webhook_payment_data_signature)

    @mute_logger(
        "odoo.addons.payment_aba_payway.controllers.main",
        "odoo.addons.payment.models.payment_transaction",
    )
    def test_webhook_notification_skips_signature_verification_for_missing_transactions(self):
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock:
            response = self._make_json_request(url, data=self.webhook_payment_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(signature_check_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_webhook_notification_confirms_transaction(self):
        """Test the processing of a webhook notification."""
        self._disable_process_patcher()
        tx = self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        self._make_signed_json_request(
            url, self.webhook_payment_data, self.webhook_payment_data_signature,
        )
        self._run_processing()
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_aba_payway.controllers.main", "odoo.addons.payment.utils")
    def test_reject_webhook_notification_with_invalid_signature(self):
        """Test that a webhook notification whose signature doesn't match its data is rejected."""
        self._disable_process_patcher()
        tx = self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        tampered_payment_data = dict(self.webhook_payment_data, original_amount=1)
        response = self._make_signed_json_request(
            url, tampered_payment_data, self.webhook_payment_data_signature,
        )
        self.assertEqual(response.status_code, 403)
        self._run_processing()
        self.assertEqual(tx.state, "draft")
