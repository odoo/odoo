# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_qfpay import const
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(QFPayCommon):
    def test_reference_length_is_at_most_128_chars(self):
        reference = self.env["payment.transaction"]._compute_reference("qfpay", prefix="x" * 300)
        self.assertLessEqual(len(reference), 128)

    def test_extract_reference_finds_reference(self):
        tx = self._create_transaction("direct")
        reference = self.env["payment.transaction"]._extract_reference("qfpay", self.payment_data)
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(amount_data, {"amount": 1111.11, "currency_code": "HKD"})

    def test_no_item_missing_from_processing_values(self):
        tx = self._create_transaction(
            "direct", payment_method_id=self.env.ref("payment_qfpay.payment_method_card").id
        )
        with patch.object(
            self.env.registry["payment.transaction"],
            "_send_api_request",
            return_value=self.mock_intent_response,
        ):
            processing_values = tx._get_specific_processing_values({})
        self.assertDictEqual(
            processing_values,
            {
                **const.SDK_CONFIG["test"],
                "picker_payment_type": "VisaMasterCardPayment",
                "payment_intent": "mock-payment-intent-token",
                "out_trade_no": "Test Transaction",
                "txamt": "111111",
                "txcurrcd": "HKD",
                "return_url": f"{tx.provider_id.get_base_url()}"
                "/payment/qfpay/return?out_trade_no=Test+Transaction",
            },
        )

    def test_failed_payment_intent_creation_sets_transaction_in_error(self):
        with patch.object(
            self.env.registry["payment.transaction"],
            "_send_api_request",
            side_effect=ValidationError("Invalid app code"),
        ):
            tx = self._create_transaction("direct")
            tx._get_processing_values()
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_qfpay.models.payment_transaction")
    def test_failed_status_query_returns_no_payment_data(self):
        tx = self._create_transaction("direct")
        with patch.object(
            self.env.registry["payment.transaction"],
            "_send_api_request",
            side_effect=ValidationError("Invalid app code"),
        ):
            payment_data = tx._qfpay_query_transaction_data()
        self.assertIsNone(payment_data)

    def test_apply_updates_sets_provider_reference(self):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["syssn"])

    def test_apply_updates_sets_payment_method(self):
        tx = self._create_transaction(
            "direct", payment_method_id=self.env.ref("payment_qfpay.payment_method_fps").id
        )
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id, self.env.ref("payment_qfpay.payment_method_card"))

    def test_apply_updates_confirms_transaction(self):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_sets_pending_transaction(self):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            **self.payment_data,
            "respcd": const.PAYMENT_STATUS_MAPPING["pending"][0],
        })
        self.assertEqual(tx.state, "pending")

    def test_apply_updates_cancels_transaction(self):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            **self.payment_data,
            "respcd": const.PAYMENT_STATUS_MAPPING["cancel"][0],
        })
        self.assertEqual(tx.state, "cancel")

    def test_apply_updates_errors_transaction(self):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            **self.payment_data,
            "respcd": const.PAYMENT_STATUS_MAPPING["error"][0],
        })
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_qfpay.models.payment_transaction")
    def test_apply_updates_sets_error_on_unknown_status(self):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            **self.payment_data,
            "respcd": "9999",
        })
        self.assertEqual(tx.state, "error")
