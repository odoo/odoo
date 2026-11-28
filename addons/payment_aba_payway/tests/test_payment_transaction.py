# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time
from werkzeug.urls import url_encode

from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.urls import urljoin

from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(AbaPaywayCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior
    def test_reference_is_singularized(self):
        """Test the singularization of reference prefixes."""
        reference = self.env["payment.transaction"]._compute_reference(self.provider.code)
        self.assertEqual(reference, "tx20111102120021")

    def test_reference_length_is_at_most_20_chars(self):
        """The computed reference must be at most 20 characters long."""
        reference = self.env["payment.transaction"]._compute_reference(self.provider.code)
        self.assertLessEqual(len(reference), 20)

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction("redirect")
        base_url = self.provider.get_base_url()
        with patch(
            "odoo.addons.payment_aba_payway.models.payment_provider.PaymentProvider"
            "._aba_payway_calculate_signature",
            return_value="dummy_signature",
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        self.maxDiff = None
        self.assertDictEqual(
            rendering_values,
            {
                "api_url": urljoin(
                    self.provider._aba_payway_get_api_url(),
                    "/api/payment-gateway/v1/payments/purchase",
                ),
                "url_params": {
                    "req_time": tx.create_date.strftime("%Y%m%d%H%M%S"),
                    "merchant_id": self.provider.aba_payway_merchant_id,
                    "tran_id": tx.reference,
                    "payment_option": const.PAYMENT_METHODS_MAPPING["card"],
                    "amount": "2213",
                    "currency": tx.currency_id.name,
                    "return_url": urljoin(base_url, const.WEBHOOK_ROUTE),
                    "skip_success_page": 1,
                    "continue_success_url": urljoin(
                        base_url,
                        f"{const.PAYMENT_RETURN_ROUTE}?{url_encode({'tran_id': tx.reference})}",
                    ),
                    "payment_gate": "0",
                    "lifetime": 3,
                    "hash": "dummy_signature",
                },
            },
        )

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that no key is omitted from the rendering values."""
        tx = self._create_transaction("redirect")
        expected_input_keys = [
            "req_time",
            "merchant_id",
            "tran_id",
            "payment_option",
            "amount",
            "currency",
            "return_url",
            "skip_success_page",
            "continue_success_url",
            "payment_gate",
            "lifetime",
            "hash",
        ]
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(
            form_info["action"],
            urljoin(
                self.provider._aba_payway_get_api_url(), "/api/payment-gateway/v1/payments/purchase"
            ),
        )
        self.assertEqual(form_info["method"], "post")
        self.assertListEqual(list(form_info["inputs"].keys()), expected_input_keys)

    def test_rendering_values_contain_rounded_amount_khr(self):
        """Test that the amount is rounded down to the nearest unit for the KHR currency."""
        tx = self._create_transaction("redirect", amount=2213.75)
        rendering_values = tx._get_specific_rendering_values(None)
        self.assertEqual(rendering_values["url_params"]["amount"], "2213")

    def test_sync_from_provider_records_payment_data(self):
        """Test that the status fetched from ABA PayWay is recorded in the format of the payment
        data of webhook notifications."""
        tx = self._create_transaction("redirect")
        with (
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
                "._send_api_request",
                return_value=self.check_transaction_response,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            tx._aba_payway_sync_from_provider()
        record_mock.assert_called_once_with({
            "tran_id": tx.reference,
            "status": 0,
            "apv": "544415",
            "original_amount": self.amount,
            "original_currency": self.currency.name,
        })

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "aba_payway", self.webhook_payment_data
        )
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertDictEqual(
            amount_data,
            {"amount": tx.amount, "currency_code": tx.currency_id.name, "precision_digits": 0},
        )

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.provider_reference, self.webhook_payment_data["apv"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        for payment_type, payment_method_code in const.PAYMENT_TYPES_MAPPING.items():
            with self.subTest(payment_type=payment_type):
                tx = self._create_transaction("redirect", reference=f"tx-{payment_type}")
                payment_data = dict(self.webhook_payment_data, payment_type=payment_type)
                tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
                self.assertEqual(tx.payment_method_code, payment_method_code)

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_sets_transaction_in_error(self):
        """Test that the transaction state is set to 'error' when the payment data indicate a
        declined payment."""
        tx = self._create_transaction("redirect")
        payment_data = dict(self.webhook_payment_data, status="3")
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_aba_payway.models.payment_transaction")
    def test_apply_updates_sets_unknown_transaction_in_error(self):
        """Test that the transaction state is set to 'error' when the payment data indicate an
        unknown payment status."""
        tx = self._create_transaction("redirect")
        payment_data = dict(self.webhook_payment_data, status="99")
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.state, "error")
