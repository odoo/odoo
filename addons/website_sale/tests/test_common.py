# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWSaleCommon(WebsiteSaleCommon):
    _test_user_groups = ('sales_team.group_sale_salesman',)

    _test_user_name = 'Test Sales User'

    def test_common(self):
        self.assertEqual(self.env.company, self.website.company_id)
