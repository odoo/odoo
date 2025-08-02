# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_iyzico.tests.common import IyzicoCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(IyzicoCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Iyzico providers are filtered out from compatible providers when the
        currency is not supported. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.INR').id
        )
        self.assertNotIn(self.provider, compatible_providers)
