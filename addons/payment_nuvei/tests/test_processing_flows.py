# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_nuvei.controllers.main import NuveiController
from odoo.addons.payment_nuvei.tests.common import NuveiCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(NuveiCommon):
    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the notification
        data."""
        self._create_transaction(flow="redirect")
        url = self._build_url(NuveiController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_get_request(url, params=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction("redirect")
        url = self._build_url(NuveiController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_redirect_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(NuveiController._return_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_get_request(url, params=self.payment_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.payment_data_signature)

    @mute_logger("odoo.addons.payment_nuvei.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("redirect")
        url = self._build_url(NuveiController._webhook_url)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment_nuvei.models.payment_provider.PaymentProvider"
                "._nuvei_calculate_signature"
            ),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_args[0][0], self.payment_data_signature)

    def test_compute_signature_returns_correct_signature(self):
        signature = self.provider._nuvei_calculate_signature(self.payment_data, incoming=True)
        self.assertEqual(signature, self.payment_data_signature)
