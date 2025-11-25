# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon

CALL_API_METHOD = "odoo.addons.payment.models.payment_transaction.PaymentTransaction._send_api_request"


@tagged("post_install", "-at_install")
class TestProcessingFlows(AbaPaywayCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_webhook_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the payment data."""
        self._create_transaction("direct", reference="tx-20251128061000")
        url = self._build_url(const.PAYMENT_WEBHOOK_ROUTE)
        with patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process") as process_mock:
            self._make_json_request(url, data=self.payment_result_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_aba_payway.models.payment_provider")
    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_valid_enrichment_triggers_processing(self):
        """Test that a valid enrichment response triggers the processing of the payment data."""
        self._create_transaction("direct", reference="tx-20251128061000")
        url = self._build_url(const.PAYMENT_WEBHOOK_ROUTE)
        with patch(CALL_API_METHOD, new=self._valid_enrichment_mock):
            with patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process") as process_mock:
                self._make_json_request(url, data=self.payment_result_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_aba_payway.models.payment_provider")
    @mute_logger("odoo.addons.payment_aba_payway.controllers.main")
    def test_invalid_enrichment_raises_error(self):
        """Test that an invalid enrichment response throws an error."""
        self._create_transaction("direct", reference="tx-20251128061000")
        url = self._build_url(const.PAYMENT_WEBHOOK_ROUTE)
        with patch(CALL_API_METHOD, new=self._invalid_enrichment_mock):
            with patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._process") as process_mock:
                self._make_json_request(url, data=self.payment_result_data)
            self.assertEqual(process_mock.call_count, 0)

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------

    def _valid_enrichment_mock(self, endpoint, params):
        if endpoint == "/api/payment-gateway/v1/payments/check-transaction-2":
            return self.check_transaction_data
        raise UserError("Unexpected endpoint called during a test: %s with params %s." % (endpoint, params))

    def _invalid_enrichment_mock(self, endpoint, params):
        if endpoint == "/api/payment-gateway/v1/payments/check-transaction-2":
            return {"status": {"code": 6, "message": "Transaction not found", "tran_id": "tx-20251128061000"}}
        raise UserError("Unexpected endpoint called during a test: %s with params %s." % (endpoint, params))
