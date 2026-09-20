# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_buckaroo.tests.common import BuckarooCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(BuckarooCommon):
    def test_signature_calculation_for_outgoing_data(self):
        """Test that the calculated signature matches the expected signature for outgoing data."""
        calculated_signature = self.buckaroo._buckaroo_generate_digital_sign(
            {
                "brq_websitekey": self.buckaroo.buckaroo_website_key,
                "brq_amount": self.amount,
                "brq_currency": self.currency.name,
                "brq_invoicenumber": self.reference,
            },
            incoming=False,
        )
        self.assertEqual(calculated_signature, "918337f8aab8964cfa3c4618582ba5fc405d7529")

    def test_signature_calculation_for_incoming_data(self):
        """Test that the calculated signature matches the expected signature for incoming data."""
        calculated_signature = self.buckaroo._buckaroo_generate_digital_sign(
            self.async_payment_data, incoming=True
        )
        self.assertEqual(calculated_signature, self.async_payment_data_signature)

    def test_signature_is_computed_based_on_lower_case_data_keys(self):
        """Test that lower case keys are used to execute the case-insensitive sort."""
        computed_signature = self.provider._buckaroo_generate_digital_sign(
            {"brq_a": "1", "brq_b": "2", "brq_c_first": "3", "brq_csecond": "4", "brq_D": "5"},
            incoming=False,
        )
        self.assertEqual(
            computed_signature,
            "937cca8f486b75e93df1e9811a5ebf43357fc3f2",
            msg="The signing string items should be ordered based on a lower-case copy of the keys",
        )
