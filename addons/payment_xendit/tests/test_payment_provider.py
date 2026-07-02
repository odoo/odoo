# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(XenditCommon):
    _test_groups = None  # FIXME list needed groups

    def test_not_available_for_unsupported_currencies(self):
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id
        )
        self.assertNotIn(self.xendit, available_providers)
