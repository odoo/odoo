# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payu import const
from odoo.addons.payment_payu.tests.common import PayuCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PayuCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_payu.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch("odoo.addons.payment_payu.controllers.main.PayuController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_payu.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("redirect")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch("odoo.addons.payment_payu.controllers.main.PayuController._verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_payu.controllers.main")
    def test_returning_from_payment_triggers_signature_check(self):
        """Test that receiving a redirect notification triggers a signature check."""
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch(
                "odoo.addons.payment_payu.controllers.main.PayuController._verify_signature"
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_payu.controllers.main")
    def test_webhook_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("redirect")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch(
                "odoo.addons.payment_payu.controllers.main.PayuController._verify_signature"
            ) as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(signature_check_mock.call_count, 1)
