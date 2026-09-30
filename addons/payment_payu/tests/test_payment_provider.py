# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_payu.tests.common import PayuCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(PayuCommon):
    def test_signature_calculation_for_incoming_data(self):
        """Test that the calculated signature matches the expected signature for incoming data."""
        calculated_signature = self.provider._payu_generate_signature(
            self.payment_data, incoming=True
        )
        expected_signature = (
            "8b4dea378f62cdbfcd740397591597b32d05d8904aa3fb362deb0ac612c169d6dc25d7b8cba6c64203dca1"
            "ab462adddc87b2a99fda13b7181624b6e811cb1394"
        )
        self.assertEqual(calculated_signature, expected_signature)

    def test_signature_calculation_for_outgoing_data(self):
        """Test that the calculated signature matches the expected signature for outgoing data."""
        calculated_signature = self.provider._payu_generate_signature(self.payment_data)
        expected_signature = (
            "2ef7d15c2efa7a11e19935b9d698d2acc8cba173e1c6dbb12b837be6a6c295e9b31c13fc65c669dda0fe065"
            "0d317f61b8e4dc270db2274f5dbdf5ced7bff5cc4"
        )
        self.assertEqual(calculated_signature, expected_signature)
