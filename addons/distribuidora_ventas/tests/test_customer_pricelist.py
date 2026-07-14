from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCustomerPricelist(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Tomate',
            'type': 'consu',
            'list_price': 500.0,
        })
        self.pricelist_hotel = self.env['product.pricelist'].create({
            'name': 'Precios Hotel Test',
            'item_ids': [(0, 0, {
                'applied_on': '0_product_variant',
                'product_id': self.product.id,
                'compute_price': 'fixed',
                'fixed_price': 650.0,
            })],
        })
        self.pricelist_restaurante = self.env['product.pricelist'].create({
            'name': 'Precios Restaurante Test',
            'item_ids': [(0, 0, {
                'applied_on': '0_product_variant',
                'product_id': self.product.id,
                'compute_price': 'fixed',
                'fixed_price': 580.0,
            })],
        })
        self.hotel = self.env['res.partner'].create({
            'name': 'Hotel Test',
            'property_product_pricelist': self.pricelist_hotel.id,
        })
        self.restaurante = self.env['res.partner'].create({
            'name': 'Restaurante Test',
            'property_product_pricelist': self.pricelist_restaurante.id,
        })

    def test_order_line_price_follows_customer_pricelist(self):
        order_hotel = self.env['sale.order'].create({'partner_id': self.hotel.id})
        self.env['sale.order.line'].create({
            'order_id': order_hotel.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })
        order_restaurante = self.env['sale.order'].create({'partner_id': self.restaurante.id})
        self.env['sale.order.line'].create({
            'order_id': order_restaurante.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })

        self.assertEqual(order_hotel.order_line.price_unit, 650.0)
        self.assertEqual(order_restaurante.order_line.price_unit, 580.0)
