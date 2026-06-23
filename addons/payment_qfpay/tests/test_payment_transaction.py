# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import urlencode

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_qfpay import const
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(QFPayCommon):
    def test_reference_length_is_at_most_128_chars(self):
        """Test that QFPay references are truncated to the provider's max length."""
        reference = self.env["payment.transaction"]._compute_reference("qfpay", prefix="x" * 300)
        self.assertLessEqual(len(reference), 128)

    def test_extract_reference_finds_reference(self):
        """Test that the reference is extracted from webhook data."""
        tx = self._create_transaction("direct")
        reference = self.env["payment.transaction"]._extract_reference("qfpay", self.webhook_data)
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that amount and currency are extracted and converted."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_data)
        expected_amount = payment_utils.to_major_currency_units(
            float(self.webhook_data["txamt"]), tx.currency_id
        )
        self.assertDictEqual(
            amount_data, {"amount": expected_amount, "currency_code": self.currency.name}
        )

    def test_get_specific_processing_values_returns_expected_values(self):
        """Test that processing values include payment intent, amount, and the return URL."""
        payment_transaction_model = self.env.registry["payment.transaction"]
        with patch.object(
            payment_transaction_model,
            "_send_api_request",
            autospec=True,
            return_value=self.mock_intent_response,
        ):
            tx = self._create_transaction("direct")
            values = tx._get_specific_processing_values({})

        expected_return_url = urljoin(
            tx.provider_id.get_base_url(),
            f"{const.PAYMENT_RETURN_ROUTE}?{urlencode({'out_trade_no': tx.reference})}",
        )
        expected_txamt = str(payment_utils.to_minor_currency_units(tx.amount, tx.currency_id))
        self.assertDictEqual(
            values,
            {
                "payment_intent": "mock-payment-intent-token",
                "out_trade_no": tx.reference,
                "txamt": expected_txamt,
                "txcurrcd": self.currency.name,
                "return_url": expected_return_url,
            },
        )

    def test_get_specific_processing_values_raises_on_api_error(self):
        """Test that failed payment-intent creation raises ValidationError."""
        payment_transaction_model = self.env.registry["payment.transaction"]
        with patch.object(
            payment_transaction_model,
            "_send_api_request",
            autospec=True,
            return_value={"respcd": "1001", "respmsg": "Invalid app code"},
        ):
            tx = self._create_transaction("direct")
            with self.assertRaises(ValidationError):
                tx._get_specific_processing_values({})

    def test_qfpay_query_transaction_data_returns_matching_record(self):
        """Test that transaction query returns the record matching the transaction reference."""
        tx = self._create_transaction("direct")
        payment_transaction_model = self.env.registry["payment.transaction"]
        with patch.object(
            payment_transaction_model,
            "_send_api_request",
            return_value={
                "respcd": "0000",
                "data": [{"out_trade_no": tx.reference, "respcd": "0000"}],
            },
        ):
            payment_data = tx._qfpay_query_transaction_data()

        self.assertEqual(payment_data["out_trade_no"], tx.reference)

    def test_qfpay_query_transaction_data_returns_none_on_error(self):
        """Test that transaction query returns None when QFPay responds with an error."""
        tx = self._create_transaction("direct")
        payment_transaction_model = self.env.registry["payment.transaction"]
        with patch.object(
            payment_transaction_model, "_send_api_request", return_value={"respcd": "1001"}
        ):
            payment_data = tx._qfpay_query_transaction_data()
        self.assertIsNone(payment_data)

    def test_apply_updates_confirms_transaction(self):
        """Test that success payment data sets the transaction state to done."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_sets_pending_transaction(self):
        """Test that pending response codes set the transaction state to pending."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "respcd": const.PAYMENT_STATUS_MAPPING["pending"][0],
            "respmsg": "Pending",
        })
        self.assertEqual(tx.state, "pending")

    def test_apply_updates_cancels_transaction(self):
        """Test that cancel response codes set the transaction state to cancel."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "respcd": const.PAYMENT_STATUS_MAPPING["cancel"][0],
            "respmsg": "Canceled",
        })
        self.assertEqual(tx.state, "cancel")

    def test_apply_updates_sets_error_on_unknown_status(self):
        """Test that unknown response codes set the transaction state to error."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "respcd": "9999",
            "errmsg": "Unknown status",
        })
        self.assertEqual(tx.state, "error")
