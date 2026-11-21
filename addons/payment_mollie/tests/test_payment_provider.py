# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(MollieCommon):
    def test_not_available_for_unsupported_currencies(self):
        currency_id = self.env.ref("base.AFN").id
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=currency_id
        )
        self.assertNotIn(self.mollie, available_providers)
