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
        so.set_delivery_line(self.free_delivery, 0)
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

    def test_fiscal_position_id_is_computed_from_pickup_location_partner(self):
        fp_be = self.env['account.fiscal.position'].create({
            'name': "Test BE fiscal position",
            'country_id': self.country_be.id,
            'auto_apply': True,
        })
        self.default_partner.country_id = self.country_us
        self.warehouse.partner_id.country_id = self.country_be
        so = self._create_in_store_delivery_order(
            partner_shipping_id=self.default_partner.id,
            pickup_location_data={'id': self.warehouse.id},
        )
        self.assertEqual(so.fiscal_position_id, fp_be)

    def test_setting_pickup_location_assigns_correct_fiscal_position(self):
        fp_be = self.env['account.fiscal.position'].create({
            'name': "Test BE fiscal position",
            'country_id': self.country_be.id,
            'auto_apply': True,
        })
        so = self._create_in_store_delivery_order()
        self.default_partner.country_id = self.country_be
        warehouse = self._create_warehouse()
        warehouse.partner_id = self.default_partner
        so._set_pickup_location('{"id":' + str(warehouse.id) + '}')
        self.assertEqual(so.fiscal_position_id, fp_be)

    def test_selecting_not_in_store_dm_resets_fiscal_position(self):
        fp_us = self.env['account.fiscal.position'].create({
            'name': "Test US fiscal position",
            'country_id': self.country_us.id,
            'auto_apply': True,
        })
        so = self._create_in_store_delivery_order()
        so.fiscal_position_id = fp_us
        so.set_delivery_line(self.free_delivery, 0)
        self.assertNotEqual(so.fiscal_position_id, fp_us)

    def test_free_qty_calculated_from_order_wh_if_dm_is_in_store(self):
        self.warehouse_2 = self._create_warehouse()
        self.website.warehouse_id = self.warehouse_2
        so = self._create_in_store_delivery_order()
        so.warehouse_id = self.warehouse
        free_qty = so._get_free_qty(self.storable_product)
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
        insufficient_stock_data = cart._get_insufficient_stock_data(self.warehouse.id)
        self.assertFalse(insufficient_stock_data)

    def test_product_insufficient_stock_is_unavailable(self):
        cart = self._create_in_store_delivery_order(
            order_line=[
                Command.create({
                    'product_id': self.storable_product.id,
                    'product_uom_qty': 15.0,
                })
            ]
        )
        insufficient_stock_data = cart._get_insufficient_stock_data(self.warehouse.id)
        self.assertEqual(insufficient_stock_data[cart.order_line], 10)

    def test_out_of_stock_product_is_unavailable(self):
        cart = self._create_in_store_delivery_order(
            order_line=[
                Command.create({
                    'product_id': self.product_2.id,
                    'product_uom_qty': 5.0,
                }),
            ]
        )
        insufficient_stock_data = cart._get_insufficient_stock_data(self.warehouse.id)
        self.assertIn(cart.order_line, insufficient_stock_data)

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
        insufficient_stock_data = cart._get_insufficient_stock_data(self.warehouse_2.id)
        self.assertIn(cart.order_line, insufficient_stock_data)
