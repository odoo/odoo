# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestWebsite(ClickAndCollectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_2 = cls._create_warehouse()

    def test_product_available_qty_if_in_store_dm_published(self):
        self.website.warehouse_id = self.warehouse_2
        free_qty = self.website._get_product_available_qty(self.storable_product)
        self.assertEqual(free_qty, 10)

    def test_product_available_qty_if_in_store_dm_unpublished(self):
        self.in_store_dm.is_published = False
        self.website.warehouse_id = self.warehouse_2
        free_qty = self.website._get_product_available_qty(self.storable_product)
        self.assertEqual(free_qty, 0)

    def test_product_available_qty_with_no_carrier(self):
        """
        Test that when no carrier is set on the cart, the available quantity is the
        maximum between the website warehouse and the max available in in-store warehouses.
        """
        self.website.warehouse_id = self.warehouse_2
        order = self._create_so()
        with MockRequest(self.env, website=self.website, sale_order_id=order.id):
            free_qty = self.website._get_product_available_qty(self.storable_product)
        # Should be max(0, 10) -> 10
        self.assertEqual(free_qty, 10)

    def test_product_available_qty_with_in_store_carrier(self):
        """
        Test that when an in-store carrier is selected, the available quantity is strictly
        limited to the stock at the selected pickup warehouse (warehouse_id on the cart).
        """
        self.website.warehouse_id = self.warehouse_2
        self._add_product_qty_to_wh(self.storable_product.id, 5, self.warehouse_2.lot_stock_id.id)
        order = self._create_in_store_delivery_order(
            pickup_location_data={'id': self.warehouse_2.id, 'name': 'WH1'}
        )
        with MockRequest(self.env, website=self.website, sale_order_id=order.id):
            free_qty = self.website._get_product_available_qty(self.storable_product, order=order)
        # Should be exactly 5 (specific warehouse stock), ignoring the 10 in WH1
        self.assertEqual(free_qty, 5)

    def test_product_available_qty_with_standard_carrier(self):
        """
        Test that when a standard (non-in-store) carrier is selected, the system behaves
        standardly (ignoring other in-store stocks), returning only the website warehouse stock.
        """
        self.website.warehouse_id = self.warehouse_2
        order = self._create_so(carrier_id=self.free_delivery.id)
        with MockRequest(self.env, website=self.website, sale_order_id=order.id):
            free_qty = self.website._get_product_available_qty(self.storable_product)
        # Should be 0 (website warehouse stock), ignoring the 10 in WH1
        self.assertEqual(free_qty, 0)

    def test_in_store_product_available_qty_for_order(self):
        self.in_store_dm.warehouse_ids = [Command.link(self.warehouse_2.id)]
        self._add_product_qty_to_wh(self.storable_product.id, 15, self.warehouse_2.lot_stock_id.id)
        free_qty = self.website._get_max_in_store_product_available_qty(self.storable_product)
        self.assertEqual(free_qty, 15)
