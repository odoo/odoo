# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(MercadoPagoCommon):
    def test_allow_setting_live_if_credentials_are_set(self):
        """Test that setting live a Mercado Pago provider with credentials succeeds."""
        self._assert_does_not_raise(ValidationError, self.provider.write({"is_live": True}))

    def test_prevent_setting_live_if_credentials_are_not_set(self):
        """Test that setting live a Mercado Pago provider without credentials raises a
        ValidationError."""
        # Reset the state and credentials together to avoid triggering the constraint outside of the
        # 'assertRaises'.
        self.provider.module_state = "installed"
        self.provider.action_reset_credentials()
        with self.assertRaises(ValidationError):
            self.provider.is_live = True

    def test_not_available_for_unsupported_currencies(self):
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id
        )
        self.assertNotIn(self.provider, available_providers)
