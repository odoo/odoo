# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_aba_payway import const
from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(AbaPaywayCommon):
    def test_not_available_for_unsupported_currencies(self):
        """Test that the provider is not available for unsupported currencies."""
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id
        )
        self.assertNotIn(self.provider, available_providers)

    def test_signature_calculation_for_outgoing_data(self):
        """Test that the calculated signature matches the expected signature for outgoing data."""
        calculated_signature = self.provider._aba_payway_calculate_signature({
            "req_time": "20260923120000",
            "merchant_id": self.provider.aba_payway_merchant_id,
            "tran_id": self.reference,
            "payment_option": const.PAYMENT_METHODS_MAPPING["card"],
            "amount": "2213",
            "currency": self.currency.name,
            "return_url": "https://example.com/payment/aba_payway/webhook",
            "skip_success_page": 1,
            "continue_success_url": "https://example.com/payment/status",
            "payment_gate": "0",  # Not signed
            "lifetime": 3,
        })
        self.assertEqual(
            calculated_signature,
            "iJyspOZl8VszQKQuJNpveegvn/IlsSfirGjriZeRtreE4lGU4N0rqltGlCwBEXvoiVm7GJSZ9gD4/"
            "8XymYUBpA==",
        )

    def test_signature_calculation_for_incoming_data(self):
        """Test that the calculated signature matches the expected signature for incoming data."""
        calculated_signature = self.provider._aba_payway_calculate_signature(
            self.webhook_payment_data, keys=sorted(self.webhook_payment_data)
        )
        self.assertEqual(calculated_signature, self.webhook_payment_data_signature)
