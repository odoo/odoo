from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_toss_payments import const
from odoo.addons.payment_toss_payments.tests.common import TossPaymentsCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(TossPaymentsCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_toss_payments.controllers.main")
    def test_returning_from_successful_payment_initiation_triggers_processing(self):
        """Test that successfully initiating a payment triggers the processing of the payment
        data."""
        tx = self._create_transaction("direct")
        redirect_success_params = {"orderId": tx.reference, "paymentKey": "test-pk", "amount": 750}
        url = self._build_url(const.PAYMENT_SUCCESS_RETURN_ROUTE)
        with (
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                "._send_api_request"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_http_get_request(url, params=redirect_success_params)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_toss_payments.controllers.main")
    def test_failing_to_confirm_payment_sets_the_transaction_in_error(self):
        """Test that the transaction is set in error if the payment confirmation request fails."""
        tx = self._create_transaction("direct")
        redirect_success_params = {"orderId": tx.reference, "paymentKey": "test-pk", "amount": 750}
        url = self._build_url(const.PAYMENT_SUCCESS_RETURN_ROUTE)
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._send_api_request",
            side_effect=ValidationError("dummy response"),
        ):
            self._make_http_get_request(url, params=redirect_success_params)
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_toss_payments.controllers.main")
    def test_returning_from_failing_payment_initiation_sets_transaction_in_error(self):
        """Test that failing to initiate a payment set the transaction in error."""
        tx = self._create_transaction("direct")
        url = self._build_url(const.PAYMENT_FAILURE_RETURN_ROUTE)
        access_token = payment_utils.generate_access_token(tx.reference, env=self.env)
        error_data = {
            "code": "ERR",
            "message": "Payment refused",
            "orderId": tx.reference,
            "access_token": access_token,
        }
        self._make_http_get_request(url, params=error_data)
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_toss_payments.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.webhook_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_toss_payments.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process"),
        ):
            self._make_json_request(url, data=self.webhook_data)
        self.assertEqual(signature_check_mock.call_args[0][0], self.webhook_data_signature)
