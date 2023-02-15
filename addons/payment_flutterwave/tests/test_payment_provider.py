# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_flutterwave.tests.common import FlutterwaveCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(FlutterwaveCommon):

    def test_incompatible_with_unsupported_currencies(self):
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.flutterwave, compatible_providers)

    def test_incompatible_with_validation_transactions(self):
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, 0., is_validation=True
        )
        self.assertNotIn(self.flutterwave, compatible_providers)
