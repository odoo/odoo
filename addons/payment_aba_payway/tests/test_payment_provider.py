# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(AbaPaywayCommon):
    def test_allow_setting_live_if_credentials_are_set(self):
        """Test that setting live an ABA PayWay provider with credentials succeeds."""
        self._assert_does_not_raise(ValidationError, self.provider.write({"is_live": True}))

    def test_prevent_setting_live_if_credentials_are_not_set(self):
        """Test that setting live an ABA PayWay provider without credentials raises a
        ValidationError."""
        self.provider.write({"aba_payway_merchant_id": None, "aba_payway_api_key": None})
        with self.assertRaises(ValidationError):
            self.provider.is_live = True

    def test_not_available_for_unsupported_currencies(self):
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id,
        )
        self.assertNotIn(self.provider, available_providers)

    def test_unsupported_currency_cannot_be_made_available(self):
        """Test that making an unsupported currency available raises a ValidationError."""
        with self.assertRaises(ValidationError):
            self.provider.available_currency_ids = [Command.link(self.currency_euro.id)]

    def test_signature_calculation_for_outgoing_data(self):
        """Test that the calculated signature matches the expected signature for outgoing data."""
        calculated_signature = self.provider._aba_payway_calculate_signature(
            {
                "req_time": "20260923120000",
                "merchant_id": self.provider.aba_payway_merchant_id,
                "tran_id": self.reference,
                "amount": "2213",
                "firstname": "Norbert",
                "lastname": "Buyer",
                "email": "norbert.buyer@example.com",
                "phone": "0032 12 34 56 78",
                "type": "purchase",
                "payment_option": const.PAYMENT_METHODS_MAPPING["card"],
                "return_url": "https://example.com/payment/aba_payway/webhook",
                "continue_success_url": "https://example.com/payment/status",
                "currency": self.currency.name,
                "lifetime": 3,
                "skip_success_page": 1,
                "payment_gate": 0,  # Not signed.
            },
        )
        self.assertEqual(
            calculated_signature,
            "G2jLHo/D1/SML8X47Wyrkt83dPFOTcpGUHLzOKh0VTcvIuo50eh6rEoTQF5iQhN0fvVAl54XWGgZUcgxMBIElQ==",
        )

    def test_signature_calculation_for_incoming_data(self):
        """Test that the calculated signature matches the expected signature for incoming data."""
        calculated_signature = self.provider._aba_payway_calculate_signature(
            self.webhook_payment_data, keys=sorted(self.webhook_payment_data),
        )
        self.assertEqual(calculated_signature, self.webhook_payment_data_signature)

    def test_signature_is_computed_based_on_php_string_conversion(self):
        """Test that the values are converted to strings following PHP's rules, as done by ABA
        PayWay."""
        data = {"a": 100.0, "b": 0.01, "c": 0, "d": None, "e": True, "f": False, "g": "text"}
        expected_signature = base64.b64encode(
            hmac.new(
                self.provider.aba_payway_api_key.encode(), b"1000.0101text", hashlib.sha512,
            ).digest(),
        ).decode()
        self.assertEqual(
            self.provider._aba_payway_calculate_signature(data, keys=sorted(data)),
            expected_signature,
        )
