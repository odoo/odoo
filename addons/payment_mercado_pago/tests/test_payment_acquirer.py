# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged('post_install', '-at_install')
class TestPaymentAcquirer(MercadoPagoCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Mercado Pago acquirers are filtered out from compatible acquirers when the
        currency is not supported. """
        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.acquirer, compatible_acquirers)

    def test_neutralize(self):
        """ Test that the sensitive fields of the acquirer are correctly neutralized. """
        self.env['payment.acquirer']._neutralize()
        self.assertFalse(self.acquirer.mercado_pago_access_token)
