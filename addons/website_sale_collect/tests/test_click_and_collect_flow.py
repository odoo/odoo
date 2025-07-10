# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.tests.common import HttpCase
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestClickAndCollectFlow(HttpCase, ClickAndCollectCommon):

    def test_click_and_collect_widget_as_public_user(self):
        self.storable_product.name = "Test CAC Product"
        self.provider.write(
            {
                'state': 'enabled',
                'is_published': True,
            }
        )
        self.in_store_dm.warehouse_ids[0].partner_id = self.env['res.partner'].create(
            {
                **self.dummy_partner_address_values,
                'name': "Shop 1",
                'partner_latitude': 1.0,
                'partner_longitude': 2.0,
            }
        )
        self.start_tour('/', 'website_sale_collect_widget')
