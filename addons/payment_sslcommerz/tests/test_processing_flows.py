# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_sslcommerz import const
from odoo.addons.payment_sslcommerz.tests.common import SSLCommerzCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(SSLCommerzCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_sslcommerz.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the payment
        data."""
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction."
                "_send_api_request",
                return_value=self.payment_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_sslcommerz.controllers.main")
    def test_ipn_notification_triggers_processing(self):
        """Test that receiving a valid IPN notification triggers the processing of the payment
        data."""
        self._create_transaction("redirect")
        url = self._build_url(const.IPN_ROUTE)
        with (
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction."
                "_send_api_request",
                return_value=self.payment_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_sslcommerz.controllers.main")
    def test_returning_from_payment_triggers_validation_call(self):
        """Test that receiving a redirect notification with a val_id triggers a call to the
        Order Validation API."""
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._send_api_request",
            return_value=self.payment_data,
        ) as send_request_mock:
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(send_request_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_sslcommerz.controllers.main")
    def test_missing_val_id_with_cancel_status_does_not_trigger_processing(self):
        """Test that a cancel notification is not recorded when it can't be verified against the
        Order Validation API for lack of a val_id."""
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        data = {"tran_id": self.reference, "status": "CANCELLED"}
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
        ) as record_mock:
            self._make_http_post_request(url, data=data)
        self.assertEqual(record_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_sslcommerz.controllers.main")
    def test_missing_val_id_with_success_status_does_not_trigger_processing(self):
        """Test that a successful notification is not recorded when it can't be verified against
        the Order Validation API for lack of a val_id."""
        self._create_transaction("redirect")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        data = {**self.payment_data, "val_id": ""}
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
        ) as record_mock:
            self._make_http_post_request(url, data=data)
        self.assertEqual(record_mock.call_count, 0)
