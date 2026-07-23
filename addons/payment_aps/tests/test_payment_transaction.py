# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_aps.controllers.main import APSController
from odoo.addons.payment_aps.tests.common import APSCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(APSCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test the singularization of reference prefixes."""
        reference = self.env["payment.transaction"]._compute_reference("aps")
        self.assertEqual(reference, "tx-20111102120021")

    def test_reference_contains_only_valid_characters(self):
        """Test that transaction references are made of only alphanumerics and/or '-' and '_'."""
        for prefix in (None, "", "S0001", "INV/20222/001", "dummy ref"):
            reference = self.env["payment.transaction"]._compute_reference("aps", prefix=prefix)
            self.assertRegex(reference, r"^[\w-]+$")

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        self.env["ir.config_parameter"].set_str("web.base.url", "http://127.0.0.1:8069")
        self.patch(self, "base_url", lambda: "http://127.0.0.1:8069")

        tx = self._create_transaction(flow="redirect")

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency)
        expected_values = {
            "api_url": self.provider._aps_get_api_url(),
            "url_params": {
                "command": "PURCHASE",
                "access_code": self.provider.aps_access_code,
                "merchant_identifier": self.provider.aps_merchant_identifier,
                "merchant_reference": tx.reference,
                "payment_option": "DUMMY",
                "amount": str(converted_amount),
                "currency": self.currency.name,
                "language": tx.partner_lang[:2],
                "customer_email": tx.partner_id.email_normalized,
                "return_url": self._build_url(APSController._return_url),
                "signature": "00ad434241e345c10b9e4bfeedd98a0f8af7a7335bebc045c12f5c42d7def78b",
            },
        }
        self.assertEqual(tx._get_specific_rendering_values(None), expected_values)

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the no key is not omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        expected_input_keys = [
            "command",
            "access_code",
            "merchant_identifier",
            "merchant_reference",
            "amount",
            "currency",
            "language",
            "customer_email",
            "payment_option",
            "return_url",
            "signature",
        ]
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://sbcheckout.payfort.com/FortAPI/paymentPage")
        self.assertEqual(form_info["method"], "post")
        self.assertListEqual(list(form_info["inputs"].keys()), expected_input_keys)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction(flow="redirect")
        reference = self.env["payment.transaction"]._extract_reference("aps", self.payment_data)
        self.assertEqual(tx.reference, reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["fort_id"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id, self.env.ref("payment_aps.payment_method_visa"))

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction(flow="redirect")
        amount_data = tx._extract_amount_data(self.payment_data)
        expected_amount = payment_utils.to_major_currency_units(
            float(self.payment_data["amount"]), tx.currency_id
        )
        self.assertDictEqual(
            amount_data, {"amount": expected_amount, "currency_code": self.payment_data["currency"]}
        )
