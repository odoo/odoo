# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_payfast.tests.common import PayfastCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(PayfastCommon):
    def test_only_zar_is_a_supported_currency(self):
        supported_currencies = self.payfast._get_supported_currencies()
        self.assertTrue(supported_currencies)
        self.assertTrue(all(currency.name == "ZAR" for currency in supported_currencies))

    def test_tokenization_requires_a_passphrase(self):
        """Test that a passphrase can't be removed while tokenization is enabled, since
        Payfast's tokenized-charge API requires it."""
        self.payfast.allow_tokenization = True
        with self.assertRaises(ValidationError):
            self.payfast.payfast_passphrase = False

    def test_outgoing_signature_matches_reference_value(self):
        """Test against a signature computed independently, to catch any unintended change to
        the signing algorithm (field encoding, ordering, passphrase handling, ...)."""
        values = {
            "merchant_id": self.payfast.payfast_merchant_id,
            "merchant_key": self.payfast.payfast_merchant_key,
            "return_url": "http://localhost:8069/payment/payfast/return",
            "cancel_url": "http://localhost:8069/payment/payfast/cancel",
            "notify_url": "http://localhost:8069/payment/payfast/notify",
            "name_first": "Norbert",
            "name_last": "Buyer",
            "email_address": "norbert.buyer@example.com",
            "cell_number": "+27821234567",  # Regression test for the leading '+' encoding.
            "m_payment_id": self.reference,
            "amount": f"{self.amount:.2f}",
            "item_name": self.reference,
        }
        signature = self.payfast._payfast_generate_signature(values)
        self.assertEqual(signature, "9d013e3159cf8a45847211d49d14f612")

    def test_incoming_signature_matches_reference_value(self):
        """Test against a signature computed independently, on a realistic ITN payload."""
        signature = self.payfast._payfast_generate_signature(self.notification_data, incoming=True)
        self.assertEqual(signature, self.notification_data["signature"])

    def test_build_request_url_appends_testing_param_only_in_sandbox(self):
        base_url = "https://api.payfast.co.za/subscriptions/dummy_token/adhoc"

        self.payfast.is_live = False
        self.assertEqual(
            self.payfast._build_request_url("subscriptions/dummy_token/adhoc"),
            f"{base_url}?testing=true",
        )

        self.payfast.is_live = True
        self.assertEqual(
            self.payfast._build_request_url("subscriptions/dummy_token/adhoc"), base_url
        )

    def test_build_request_headers_signs_the_request(self):
        """The signature must cover the headers merged with the JSON body, not the `testing`
        query param appended to the URL, so that its value doesn't depend on the live mode."""
        payload = {"amount": 11111, "item_name": self.reference}
        headers = self.payfast._build_request_headers(
            "POST", "subscriptions/dummy_token/adhoc", payload
        )
        self.assertEqual(
            headers["signature"],
            self.payfast._payfast_generate_api_signature({
                "merchant-id": headers["merchant-id"],
                "version": headers["version"],
                "timestamp": headers["timestamp"],
                **payload,
            }),
        )
