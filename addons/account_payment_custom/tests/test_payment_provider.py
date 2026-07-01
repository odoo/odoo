# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account_payment_custom.tests.common import AccountPaymentCustomCommon


@tagged("-at_install", "post_install")
class TestPaymentProvider(AccountPaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.auto_confirm_cron = cls.env.ref(
            "account_payment_custom.cron_auto_confirm_paid_wire_transfer_txs"
        )

    def test_wire_transfer_accounting_configuration(self):
        """Make sure the right `account.payment.method.line` is created."""
        self.assertIn(
            "wire_transfer", self.provider.journal_id.inbound_payment_method_line_ids.mapped("code")
        )

    def test_installing_provider_activates_auto_confirm_cron(self):
        """Test that the auto-confirm cron is activated when a provider is installed."""
        self.auto_confirm_cron.active = False
        self.provider._setup_provider("custom", custom_mode="wire_transfer")
        self.assertTrue(self.auto_confirm_cron.active)

    def test_uninstalling_provider_deactivates_auto_confirm_cron(self):
        """Test that the auto-confirm cron is deactivated when a provider is disabled."""
        self.auto_confirm_cron.active = True
        self.provider._remove_provider("custom", custom_mode="wire_transfer")
        self.assertFalse(self.auto_confirm_cron.active)

    def test_pay_on_invoice_provider_not_available_on_invoice(self):
        available_providers = self.pay_on_invoice_provider._find_available_providers(
            company_id=self.company_id,
            partner_id=self.partner.id,
            amount=self.amount,
            is_invoice=True,
        )
        self.assertNotIn(self.pay_on_invoice_provider, available_providers)

    def test_pay_on_invoice_provider_available_on_sale_order(self):
        available_providers = self.pay_on_invoice_provider._find_available_providers(
            company_id=self.company_id, partner_id=self.partner.id, amount=self.amount,
        )
        self.assertIn(self.pay_on_invoice_provider, available_providers)
