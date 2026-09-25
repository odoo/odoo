# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged("post_install", "-at_install")
class TestPaymentProvider(PaymobCommon):
    def test_change_paymob_account_country(self):
        """Test that changing the Paymob account country will change the currency accordingly."""
        self.provider.paymob_account_country_id = self.quick_ref("base.sa")
        self.assertEqual(self.provider.available_currency_ids.name, "SAR")
