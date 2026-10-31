# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_aps.tests.common import APSCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(APSCommon):
    def test_signature_calculation_for_outgoing_data(self):
        """Test that the calculated signature matches the expected signature for outgoing data."""
        calculated_signature = self.aps._aps_calculate_signature(
            {
                "merchant_identifier": self.aps.aps_merchant_identifier,
                "access_code": self.aps.aps_access_code,
                "merchant_reference": self.reference,
                "amount": str(payment_utils.to_minor_currency_units(self.amount, self.currency)),
                "currency": self.currency.name,
            },
            incoming=False,
        )
        self.assertEqual(
            calculated_signature, "8147dd702b28685e861576a997f69d284eb3e84334beac4a2a2d0fe5224757a7"
        )

    def test_signature_calculation_for_incoming_data(self):
        """Test that the calculated signature matches the expected signature for incoming data."""
        calculated_signature = self.aps._aps_calculate_signature(self.payment_data, incoming=True)
        self.assertEqual(calculated_signature, self.payment_data_signature)
