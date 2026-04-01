# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(MercadoPagoCommon):

    def test_allow_enabling_if_credentials_are_set(self):
        """ Test that enabling a Mercado Pago provider with credentials succeeds. """
        self._assert_does_not_raise(ValidationError, self.provider.write({'state': 'enabled'}))

    def test_prevent_enabling_if_credentials_are_not_set(self):
        """ Test that enabling a Mercado Pago provider without credentials raises a ValidationError.
        """
        # Reset the state and credentials together to avoid triggering the constraint outside of the
        # 'assertRaises'.
        self.provider.action_reset_credentials()
        with self.assertRaises(ValidationError):
            self.provider.state = 'enabled'

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Mercado Pago providers are filtered out from compatible providers when the
        currency is not supported. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.provider, compatible_providers)
