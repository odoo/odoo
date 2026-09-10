# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(AuthorizeCommon):
    def test_not_available_for_unsupported_currencies(self):
        # Note: in the test common, 'USD' is specified as the currency linked to the user account.
        unsupported_currency = self._enable_currency("CHF")
        providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=unsupported_currency.id
        )
        self.assertNotIn(self.authorize, providers)

    def test_available_for_supported_currencies(self):
        providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_usd.id
        )
        self.assertIn(self.authorize, providers)

    def test_validation_amount_and_currency(self):
        self.assertEqual(self.authorize.available_currency_ids[0], self.currency_usd)
        self.assertEqual(self.authorize._get_validation_amount(), 0.01)
        self.assertEqual(self.authorize._get_validation_currency(), self.currency_usd)
