# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.urls import urljoin

from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(AbaPaywayCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test the singularization of reference prefixes."""
        reference = self.env["payment.transaction"]._compute_reference(self.provider.code)
        self.assertEqual(reference, "tx20111102120021")

    def test_reference_length_is_at_most_20_chars(self):
        """The computed reference must be at most 20 characters long."""
        reference = self.env["payment.transaction"]._compute_reference(self.provider.code)
        self.assertLessEqual(len(reference), 20)

    def test_no_item_missing_from_processing_values(self):
        """Test that the processing values are conform to the transaction fields."""
        tx = self._create_transaction("direct")
        base_url = self.provider.get_base_url()
        with patch(
            "odoo.addons.payment_aba_payway.models.payment_provider.PaymentProvider"
            "._aba_payway_calculate_signature",
            return_value="dummy_signature",
        ):
            processing_values = tx._get_specific_processing_values({})
        self.maxDiff = None
        self.assertDictEqual(
            processing_values,
            {
                "req_time": tx.create_date.strftime("%Y%m%d%H%M%S"),
                "merchant_id": self.provider.aba_payway_merchant_id,
                "tran_id": tx.reference,
                "amount": "2213",
                "firstname": "Norbert",
                "lastname": "Buyer",
                "email": tx.partner_email,
                "phone": tx.partner_phone,
                "type": "purchase",
                "payment_option": const.PAYMENT_METHODS_MAPPING["card"],
                "return_url": urljoin(base_url, const.WEBHOOK_ROUTE),
                "continue_success_url": urljoin(base_url, "/payment/status"),
                "currency": tx.currency_id.name,
                "lifetime": 3,
                "skip_success_page": 1,
                "payment_gate": 0,
                "form_url": urljoin(
                    self.provider._aba_payway_get_api_url(),
                    "/api/payment-gateway/v1/payments/purchase",
                ),
                "hash": "dummy_signature",
            },
        )

    def test_processing_values_contain_rounded_amount_khr(self):
        """Ensure that for KHR currency, the processing values contain the amount rounded down to
        the nearest unit."""
        tx = self._create_transaction("direct", amount=2213.75)
        processing_values = tx._get_specific_processing_values({})
        self.assertEqual(processing_values["amount"], "2213")

    def test_processing_values_omit_missing_partner_details(self):
        """Test that missing partner details are sent as empty strings."""
        partner = self.env["res.partner"].create({"name": "Norbert Buyer"})
        tx = self._create_transaction("direct", partner_id=partner.id)
        processing_values = tx._get_specific_processing_values({})
        self.assertEqual(processing_values["email"], "")
        self.assertEqual(processing_values["phone"], "")

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("direct")
        reference = self.env["payment.transaction"]._extract_reference(
            "aba_payway", self.webhook_payment_data,
        )
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertDictEqual(
            amount_data,
            {"amount": tx.amount, "currency_code": tx.currency_id.name, "precision_digits": 0},
        )

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.provider_reference, self.webhook_payment_data["apv"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        for payment_type, payment_method_code in const.PAYMENT_TYPES_MAPPING.items():
            with self.subTest(payment_type=payment_type):
                tx = self._create_transaction("direct", reference=f"tx-{payment_type}")
                payment_data = dict(self.webhook_payment_data, payment_type=payment_type)
                tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
                self.assertEqual(tx.payment_method_code, payment_method_code)

    def test_apply_updates_keeps_payment_method_for_unknown_payment_type(self):
        """Test that the payment method is kept when the payment type is unknown."""
        tx = self._create_transaction("direct")
        payment_data = dict(self.webhook_payment_data, payment_type="Unknown")
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.payment_method_id, self.payment_method_card)

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_aba_payway.models.payment_transaction")
    def test_apply_updates_sets_transaction_in_error(self):
        """Test that the transaction state is set to 'error' when the payment data indicate an
        unknown payment status."""
        tx = self._create_transaction("direct")
        payment_data = dict(self.webhook_payment_data, status="3")
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.state, "error")

    def test_apply_updates_sets_transaction_in_error_for_missing_status(self):
        """Test that the transaction state is set to 'error' when the payment data have no payment
        status."""
        tx = self._create_transaction("direct")
        payment_data = dict(self.webhook_payment_data)
        del payment_data["status"]
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.state, "error")
