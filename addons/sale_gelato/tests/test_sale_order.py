# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.sale_gelato.tests.common import GelatoCommon


@tagged('post_install', '-at_install')
class TestGelatoSaleOrder(GelatoCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_allow_adding_generic_service_product_to_gelato_order(self):
        """Test that adding a non-gelato, service product to a Gelato order is allowed."""
        self.env['sale.order.line'].create({
            'product_id': self.service_product.id,
            'order_id': self.gelato_order.id,
        })
        self.assertEqual(len(self.gelato_order.order_line.ids), 2)

    def test_allow_modifying_generic_service_product_on_gelato_order(self):
        """Test that adding a non-gelato, service product to a Gelato order is allowed."""
        order_line = self.env['sale.order.line'].create({
            'product_id': self.service_product.id,
            'order_id': self.gelato_order.id,
        })
        service_product_2 = self.service_product.copy()
        order_line.product_id = service_product_2.id
        self.assertEqual(order_line.product_id, service_product_2)

    def test_prevent_adding_generic_goods_product_to_gelato_order(self):
        """Test that adding a non-gelato goods product to Gelato order is not possible."""
        with self.assertRaises(ValidationError):
            self.env['sale.order.line'].create({
                'product_id': self.product.id,
                'order_id': self.gelato_order.id,
            })

    def test_prevent_modifying_generic_service_product_to_goods_product_on_gelato_order(self):
        """Test that adding a non-gelato goods product to Gelato order is not possible."""
        order_line = self.env['sale.order.line'].create({
            'product_id': self.service_product.id,
            'order_id': self.gelato_order.id,
        })
        with self.assertRaises(ValidationError):
            order_line.product_id = self.product.id
