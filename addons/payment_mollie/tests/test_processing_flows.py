# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mollie.controllers.main import MollieController
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(MollieCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        self._create_transaction("direct")
        url = self._build_url(MollieController._return_url)
        with (
            self._mock_send_api_request(return_value=self.payment_data),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("direct")
        url = self._build_url(MollieController._webhook_url)
        with (
            self._mock_send_api_request(return_value=self.payment_data),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_return_from_checkout_redirects_when_payment_data_unavailable(self):
        self._create_transaction("redirect")
        url = self._build_url(MollieController._return_url)
        with self._mock_send_api_request(side_effect=ValidationError("Service Unavailable")):
            response = self._make_http_get_request(url, params=self.payment_data)
        self.assertTrue(response.url.endswith("/payment/status"))

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_webhook_notification_is_rejected_when_payment_data_unavailable(self):
        self._create_transaction("redirect")
        url = self._build_url(MollieController._webhook_url)
        with self._mock_send_api_request(side_effect=ValidationError("Service Unavailable")):
            response = self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(response.status_code, 503)
