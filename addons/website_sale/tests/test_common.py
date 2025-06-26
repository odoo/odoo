# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWSaleCommon(WebsiteSaleCommon):

    def test_common(self):
        self.assertEqual(self.env.company, self.website.company_id)
        self.assertEqual(self.pricelist.currency_id, self.env.company.currency_id)
