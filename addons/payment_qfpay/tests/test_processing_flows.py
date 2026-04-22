# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_qfpay import const
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(QFPayCommon, PaymentHttpCommon):
    def _post_webhook(self, raw_body, signature):
        return self.url_open(
            self._build_url(const.WEBHOOK_ROUTE),
            data=raw_body,
            headers={"Content-Type": "application/json", "X-QF-SIGN": signature},
            method="POST",
        )

    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_returning_from_payment_triggers_processing(self):
        tx = self._create_transaction("direct")
        url = self._build_url(const.PAYMENT_RETURN_ROUTE)
        with (
            patch(
                "odoo.addons.payment_qfpay.models.payment_transaction.PaymentTransaction"
                "._qfpay_query_transaction_data",
                return_value=self.payment_data,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(url, params={"out_trade_no": tx.reference})
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_returning_from_payment_skips_query_for_final_transaction(self):
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
    def test_webhook_notification_triggers_signature_check(self):
        self._create_transaction("direct")
        with (
            patch("odoo.addons.payment.utils.verify_signature") as signature_check_mock,
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"),
        ):
            self._post_webhook(self.webhook_raw_body, self.webhook_signature)
        self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_webhook_notification_triggers_processing(self):
        self._create_transaction("direct")
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
        ) as record_mock:
            self._post_webhook(self.webhook_raw_body, self.webhook_signature)
        self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_qfpay.controllers.main")
    def test_webhook_notification_skips_processing_for_unsupported_types(self):
        self._create_transaction("direct")
        raw_body = json.dumps({**self.webhook_data, "notify_type": "refund"}).encode("utf-8")
        with (
            patch("odoo.addons.payment.utils.verify_signature"),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._post_webhook(raw_body, self.webhook_signature)
        self.assertEqual(record_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_qfpay.controllers.main", "odoo.addons.payment.utils")
    def test_webhook_notification_with_invalid_signature_rejects_processing(self):
        self._create_transaction("direct")
        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
        ) as record_mock:
            self._post_webhook(self.webhook_raw_body, "invalid_signature")
        self.assertEqual(record_mock.call_count, 0)
