# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account_payment_custom.tests.common import AccountPaymentCustomCommon


@tagged("-at_install", "post_install")
class TestPaymentProvider(AccountPaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wire_transfer_cron = cls.env.ref(
            "account_payment_custom.cron_auto_confirm_paid_wire_transfer_txs"
        )

    def test_wire_transfer_accounting_configuration(self):
        """Make sure the right `account.payment.method.line` is created."""
        self.assertIn(
            "wire_transfer", self.provider.journal_id.inbound_payment_method_line_ids.mapped("code")
        )

    def test_enabling_provider_activates_processing_cron(self):
        """Test that the post-processing cron is activated when a provider is enabled."""
        self.env["payment.provider"].search([]).state = "disabled"  # Reset providers' state.
        for enabled_state in ("enabled", "test"):
            self.wire_transfer_cron.active = False  # Reset the cron's active field.
            self.provider.state = "disabled"  # Prepare the provider for enabling.
            self.provider.state = enabled_state
            self.assertTrue(self.wire_transfer_cron.active)

    def test_disabling_provider_deactivates_processing_cron(self):
        """Test that the post-processing cron is deactivated when a provider is disabled."""
        self.env["payment.provider"].search([]).state = "disabled"  # Reset providers' state.
        for enabled_state in ("enabled", "test"):
            self.wire_transfer_cron.active = True  # Reset the cron's active field.
            self.provider.state = enabled_state  # Prepare the provider for disabling.
            self.provider.state = "disabled"
            self.assertFalse(self.wire_transfer_cron.active)
