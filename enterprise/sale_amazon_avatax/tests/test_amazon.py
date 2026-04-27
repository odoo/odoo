# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged

from odoo.addons.sale_amazon.tests import common


@tagged('post_install', '-at_install')
class TestAmazon(common.TestAmazonCommon):

    def test_recompute_subtotal_returns_subtotal_tax_excluded_when_avatax(self):
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': "Avatax FP", 'is_avatax': True
        })
        taxes = self.env['account.tax'].create({'name': "Fake expensive tax", 'amount': 80})
        subtotal, tax_amount = 100, 45
        currency = self.account.company_id.currency_id
        recomputed_subtotal = self.account._recompute_subtotal(
            subtotal, tax_amount, taxes, currency, fiscal_position
        )

        msg = "Subtotal returned when the fiscal position is Avatax shouldn't include the taxes."
        self.assertEqual(recomputed_subtotal, subtotal, msg=msg)
