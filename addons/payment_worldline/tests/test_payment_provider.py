# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_worldline.tests.common import WorldlineCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(WorldlineCommon):
    def test_calculate_signature_returns_correct_signature(self):
        """Test that the calculated signature matches the expected signature."""
        calculated_signature = self.worldline._worldline_calculate_signature(
            "POST",
            "hostedcheckouts",
            "application/json; charset=utf-8",
            "Thu, 13 Aug 2026 12:00:00 GMT",
        )
        self.assertEqual(calculated_signature, "Z8CLlPKhvJ99V4uCY1G0P/KSaCckqiuAVqVrZm3sdSA=")

    def test_calculate_signature_includes_idempotency_key(self):
        """Test that the idempotency key is included in the signing string when provided."""
        calculated_signature = self.worldline._worldline_calculate_signature(
            "POST",
            "hostedcheckouts",
            "application/json; charset=utf-8",
            "Thu, 13 Aug 2026 12:00:00 GMT",
            idempotency_key="abc-123",
        )
        self.assertEqual(calculated_signature, "6UbiOjYEG2Ms5j10oNbWkIg0CgM0F5DxJuYGoqVKW0M=")
