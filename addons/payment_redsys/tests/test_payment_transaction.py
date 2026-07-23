# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_redsys.tests.common import RedsysCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(RedsysCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test that the reference is always recomputed with a timestamp-based prefix, regardless
        of any custom prefix passed."""
        reference = self.env["payment.transaction"]._compute_reference(
            provider_code="redsys", prefix="should not be used"
        )
        expected_prefix = str(int(fields.Datetime.now().timestamp()))[-10:]
        self.assertEqual(reference, expected_prefix)

    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be made of alphanumeric characters."""
        reference = self.env["payment.transaction"]._compute_reference(provider_code="redsys")
        self.assertTrue(reference.isalnum())

    def test_reference_length_is_between_9_and_12_chars(self):
        """The computed reference must be between 9 and 12 characters."""
        reference = self.env["payment.transaction"]._compute_reference(provider_code="redsys")
        self.assertTrue(9 <= len(reference) <= 12)

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")

        expected_values = {
            "api_url": tx.provider_id._build_request_url("/realizarPago"),
            "url_params": tx._redsys_prepare_request_payload(),
        }

        self.assertEqual(tx._get_specific_rendering_values(None), expected_values)

    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_redsys.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com", "url_params": {}},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "post")
        self.assertDictEqual(form_info["inputs"], {})

    def test_no_item_missing_from_merchant_parameters(self):
        """Test that all important items are present in the merchant parameters."""
        tx = self._create_transaction(flow="redirect")
        merchant_parameters = tx._redsys_prepare_merchant_parameters()
        converted_amount = payment_utils.to_minor_currency_units(tx.amount, tx.currency_id)
        self.assertEqual(merchant_parameters["DS_MERCHANT_AMOUNT"], str(converted_amount))
        self.assertEqual(merchant_parameters["DS_MERCHANT_CURRENCY"], tx.currency_id.iso_numeric)
        self.assertEqual(merchant_parameters["DS_MERCHANT_ORDER"], tx.reference)
        self.assertEqual(merchant_parameters["DS_MERCHANT_PAYMETHODS"], "C")  # credit card
        self.assertTrue("DS_MERCHANT_EMV3DS" in merchant_parameters)

    def test_no_item_missing_from_merchant_parameters_for_tokenization(self):
        """Test that all important items are present in the merchant parameters when the transaction
        is tokenized."""
        tx = self._create_transaction("redirect", tokenize=True)
        payload = tx._redsys_prepare_merchant_parameters()
        self.assertEqual(payload["DS_MERCHANT_COF_INI"], "S")
        self.assertEqual(payload["DS_MERCHANT_COF_TYPE"], "R")
        self.assertEqual(payload["DS_MERCHANT_IDENTIFIER"], "REQUIRED")

    def test_no_item_missing_from_merchant_parameters_for_token_payments(self):
        """Test that all important items are present in the merchant parameters when payment by
        token."""
        token = self._create_token(provider_ref=self.provider_ref)
        tx = self._create_transaction("redirect", token_id=token.id)
        payload = tx._redsys_prepare_merchant_parameters()
        self.assertEqual(payload["DS_MERCHANT_COF_TYPE"], "R")
        self.assertEqual(payload["DS_MERCHANT_DIRECTPAYMENT"], "true")
        self.assertEqual(payload["DS_MERCHANT_EXCEP_SCA"], "MIT")
        self.assertEqual(payload["DS_MERCHANT_IDENTIFIER"], tx.token_id.provider_ref)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "redsys", self.merchant_parameters
        )
        self.assertEqual(tx.reference, reference)

    def test_search_by_reference_returns_tx(self):
        """Test that the transaction is returned from the payment data."""
        tx = self._create_transaction("redirect")
        self.assertEqual(
            tx,
            self.env["payment.transaction"]._search_by_reference(
                "redsys", self.merchant_parameters
            ),
        )

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated according to the brand."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.merchant_parameters)
        self.assertEqual(tx.payment_method_id, self.provider._get_pm_from_code("visa"))

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.merchant_parameters)
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.merchant_parameters)
        self.assertDictEqual(
            amount_data, {"amount": self.amount, "currency_code": self.currency_euro.name}
        )

    def test_extract_token_values_maps_fields_correctly(self):
        """Test that the token values are extracted correctly from the payment data."""
        tx = self._create_transaction(flow="redirect")
        token_values = tx._extract_token_values(self.token_merchant_data)
        self.assertEqual(token_values["provider_ref"], "test_identifier_123")
        self.assertEqual(token_values["payment_details"], "0003")
