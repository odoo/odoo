# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestClickAndCollectFlow(HttpCase, ClickAndCollectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storable_product.name = "Test CAC Product"
        cls.provider.write(
            {
                'state': 'enabled',
                'is_published': True,
            }
        )
        cls.in_store_dm.warehouse_ids[0].partner_id = cls.env['res.partner'].create(
            {
                **cls.dummy_partner_address_values,
                'name': "Shop 1",
                'partner_latitude': 1.0,
                'partner_longitude': 2.0,
            }
        )

    def test_buy_with_click_and_collect_as_public_user(self):
        """
        Test the basic flow of buying with click and collect as a public user with more than
        one delivery method available
        """
        self.start_tour('/', 'website_sale_collect_buy_product')

    def test_allow_out_of_stock_collect(self):
        """Test that click & collect allows ordering out of stock products when enabled."""
        self.storable_product.allow_out_of_stock_order = True
        self._add_product_qty_to_wh(self.storable_product.id, 0, self.warehouse.lot_stock_id.id)
        self.assertFalse(self.storable_product.free_qty)
        self.start_tour('/', 'website_sale_collect_buy_product')
