# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import InStoreCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(InStoreCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_2 = cls._create_product()

    def test_set_delivery_line_recomputes_so_wh_when_dm_is_not_in_store(self):
        self.warehouse_2 = self._create_warehouse()
        self.website.warehouse_id = self.warehouse
        so = self._create_so_in_store_dm(warehouse_id=self.warehouse_2.id)
        so.set_delivery_line(self.free_delivery, 0)
        self.assertEqual(so.warehouse_id, self.warehouse)

    def test_set_pickup_location_sets_wh_on_so(self):
        so = self._create_so_in_store_dm()
        so._set_pickup_location('{"id":' + str(self.warehouse.id) + '}')
        self.assertEqual(so.warehouse_id, self.warehouse)

    def test_get_unavailable_product_lines(self):
        cart = self._create_so_in_store_dm(
            order_line=[
                Command.create({
                    'product_id': self.storable_product.id,
                    'product_uom_qty': 5.0,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_uom_qty': 5.0,
                }),
            ]
        )
        unavailable_ol = cart._get_unavailable_order_lines(self.warehouse.id)
        self.assertIn(self.product_2.id, unavailable_ol.product_id.ids)
        self.assertNotIn(self.storable_product.id, unavailable_ol.product_id.ids)

    def test_check_cart_is_ready_to_be_paid_raise_when_products_are_out_of_stock(self):
        cart = self._create_so_in_store_dm(order_line=[Command.create({
            'product_id': self.product_2.id,
            'product_uom_qty': 5.0,
        })])
        cart.warehouse_id = self.warehouse
        with self.assertRaises(ValidationError):
            cart._check_cart_is_ready_to_be_paid()

    def test_verify_updated_quantity_skipped_when_in_store_dm_is_activated(self):
        cart = self._create_so_in_store_dm()
        new_qty, warnings = cart._verify_updated_quantity(cart.order_line, self.product_2.id, 10)
        self.assertEqual(new_qty, 10)
        self.assertEqual(warnings, '')
