# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(XenditCommon):
    def test_not_available_for_unsupported_currencies(self):
        available_providers = self.env["payment.provider"]._find_available_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref("base.AFN").id
        )
        self.assertNotIn(self.xendit, available_providers)

    def test_incompatible_with_validation_transactions(self):
        """Test that Xendit doesn't provide a redirect form for validation operations."""
        self.assertIsNone(self.xendit._get_redirect_form_view(is_validation=True))
