# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo import Command

from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(MercadoPagoCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Mercado Pago providers are filtered out from compatible providers when the
        currency is not supported. """
        # AFN is enabled on this database, but is not supported by Mercado Pago
        self._enable_currency('AFN')
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )

        # ARS is supported in Mercado Pago, but is not enabled on this database
        self.assertNotIn(self.provider, compatible_providers)

        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.ARS').id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_add_inactive_currency_to_available_currencies(self):
        """ Test that adding a non enabled supported currency to the provider's available currencies fails. """
        inactive_currency_id = self.env.ref('base.AFN').id
        with self.assertRaises(ValidationError):
            self.provider.write({'available_currency_ids': [Command.link(inactive_currency_id)]})
