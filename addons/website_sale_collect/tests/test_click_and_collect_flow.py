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

    def test_click_and_collect_visibility(self):
        """ Check that the click and collect website buttons are invisible for rental products since the feature is currently unsupported.
        """
        if self.env['ir.module.module']._get('sale_renting').state != 'installed':
            self.skipTest("If the 'sale_renting' module isn't installed, we can't test rent_ok!")
        self.assertTrue(self.storable_product.get_show_click_and_collect_availability())
        self.storable_product.rent_ok = True
        self.assertFalse(self.storable_product.get_show_click_and_collect_availability())
