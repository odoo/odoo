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

    def test_default_location_is_set_for_pick_up_in_store(self):
        """
        Verify that when `Pick Up In Store` is the only active delivery method with the only wh,
        the checkout flow automatically sets the default store location.
        """
        self.env['delivery.carrier'].search([]).active = False
        self.in_store_dm.active = True
        self.start_tour('/', 'website_sale_collect_buy_product_default_location_pick_up_in_store')
