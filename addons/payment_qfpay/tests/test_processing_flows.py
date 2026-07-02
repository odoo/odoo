# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_qfpay import const
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(QFPayCommon, PaymentHttpCommon):
    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_redirect_notification_triggers_transaction_query_and_processing(self):
        """Test that return notifications query and process the transaction data."""
        tx = self._create_transaction("direct")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)

        with (
            patch(
                "odoo.addons.payment_qfpay.models.payment_transaction.PaymentTransaction"
                "._qfpay_query_transaction_data",
                return_value=self.webhook_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params={"out_trade_no": tx.reference})

        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_redirect_notification_skips_query_for_final_transaction(self):
        """Test that return notifications do not query already finalized transactions."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._set_done()
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)

        with patch(
            "odoo.addons.payment_qfpay.models.payment_transaction.PaymentTransaction"
            "._qfpay_query_transaction_data"
        ) as query_mock:
            self._make_http_get_request(url, params={"out_trade_no": tx.reference})

        self.assertEqual(query_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_webhook_notification_triggers_signature_check_and_processing(self):
        """Test that a valid webhook verifies signature and processes the transaction."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)

        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self.url_open(
                url,
                data=self.webhook_raw_body,
                headers={"Content-Type": "application/json", "X-QF-SIGN": self.webhook_signature},
                method="POST",
            )

        self.assertEqual(signature_check_mock.call_count, 1)
        self.assertEqual(record_mock.call_count, 1)
