# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(ClickAndCollectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_2 = cls._create_product()

    def test_warehouse_is_updated_when_changing_delivery_line(self):
        self.warehouse_2 = self._create_warehouse()
        self.website.warehouse_id = self.warehouse
        so = self._create_in_store_delivery_order(warehouse_id=self.warehouse_2.id)
        so._set_delivery_method(self.free_delivery)
        self.assertEqual(so.warehouse_id, self.warehouse)

    def test_setting_pickup_location_assigns_warehouse(self):
        so = self._create_in_store_delivery_order()
        so._set_pickup_location('{"id":' + str(self.warehouse.id) + '}')
        self.assertEqual(so.warehouse_id, self.warehouse)

    def test_warehouse_is_not_reset_on_public_user_checkout(self):
        warehouse_2 = self._create_warehouse()
        so = self._create_in_store_delivery_order(partner_id=self.public_user.id)
        so._set_pickup_location('{"id":' + str(warehouse_2.id) + '}')
        # change the partner_id as would happen in a checkout
        so.partner_id = self.partner.id
        self.assertEqual(so.warehouse_id, warehouse_2)

    def test_warehouse_is_computed_based_on_pickup_location(self):
        warehouse_2 = self._create_warehouse()
        so = self._create_in_store_delivery_order(pickup_location_data={'id': warehouse_2.id})
        self.assertEqual(so.warehouse_id, warehouse_2)

    def test_setting_pickup_location_assigns_correct_fiscal_position(self):
        fp_us = self.env['account.fiscal.position'].create({
            'name': "Test US fiscal position",
            'country_id': self.country_us.id,
            'auto_apply': True,
        })
        so = self._create_in_store_delivery_order()
        self.default_partner.country_id = self.country_us
        warehouse = self._create_warehouse()
        warehouse.partner_id = self.default_partner
        so._set_pickup_location('{"id":' + str(warehouse.id) + '}')
        self.assertEqual(so.fiscal_position_id, fp_us)

    def test_selecting_not_in_store_dm_resets_fiscal_position(self):
        fp_us = self.env['account.fiscal.position'].create({
            'name': "Test US US fiscal position",
            'country_id': self.country_us.id,
            'auto_apply': True,
        })
        so = self._create_in_store_delivery_order()
        so.fiscal_position_id = fp_us
        so._set_delivery_method(self.free_delivery)
        self.assertNotEqual(so.fiscal_position_id, fp_us)

    def test_free_qty_calculated_from_order_wh_if_dm_is_in_store(self):
        self.warehouse_2 = self._create_warehouse()
        self.website.warehouse_id = self.warehouse_2
        so = self._create_in_store_delivery_order()
        so.warehouse_id = self.warehouse
        _, free_qty = so._get_cart_and_free_qty(self.storable_product)
        self.assertEqual(free_qty, 10)

    def test_prevent_buying_out_of_stock_products(self):
        cart = self._create_in_store_delivery_order(order_line=[Command.create({
            'product_id': self.product_2.id,
            'product_uom_qty': 5.0,
        })])
        cart.warehouse_id = self.warehouse
        with self.assertRaises(ValidationError):
            cart._check_cart_is_ready_to_be_paid()

    def test_product_in_stock_is_available(self):
        cart = self._create_in_store_delivery_order(
            order_line=[
                Command.create({
                    'product_id': self.storable_product.id,
                    'product_uom_qty': 5.0,
                })
            ]
        )
        unavailable_ol = cart._get_unavailable_order_lines(self.warehouse.id)
        self.assertFalse(unavailable_ol.product_id.ids)

    def test_out_of_stock_product_is_unavailable(self):
        cart = self._create_in_store_delivery_order(
            order_line=[
                Command.create({
                    'product_id': self.product_2.id,
                    'product_uom_qty': 5.0,
                }),
            ]
        )
        unavailable_ol = cart._get_unavailable_order_lines(self.warehouse.id)
        self.assertIn(self.product_2.id, unavailable_ol.product_id.ids)

    def test_product_in_different_warehouse_is_unavailable(self):
        self.warehouse_2 = self._create_warehouse()
        cart = self._create_in_store_delivery_order(
            order_line=[
                Command.create({
                    'product_id': self.storable_product.id,
                    'product_uom_qty': 5.0,
                })
            ]
        )
        unavailable_ol = cart._get_unavailable_order_lines(self.warehouse_2.id)
        self.assertIn(self.storable_product.id, unavailable_ol.product_id.ids)
