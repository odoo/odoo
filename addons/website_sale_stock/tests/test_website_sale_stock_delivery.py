# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.http import request

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.delivery.tests.common import DeliveryCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockDeliveryController(PaymentCommon, WebsiteSaleCommon, DeliveryCommon):

    def test_validate_payment_with_no_available_delivery_method(self):
        """
        An error should be raised if you try to validate an order with a storable
        product without any delivery method available
        """
        storable_product = self.env['product.product'].create([{
            'name': 'Storable Product',
            'sale_ok': True,
            'is_storable': True,
            'website_published': True,
        }])
        carriers = self.env['delivery.carrier'].search([])
        carriers.write({'website_published': False})

        WebsiteSaleCartController = Cart()
        WebsiteSaleController = WebsiteSale()
        with MockRequest(self.env, website=self.website):
            WebsiteSaleCartController.add_to_cart(
                product_template_id=storable_product.product_tmpl_id,
                product_id=storable_product.id,
                quantity=1,
            )
            with self.assertRaises(ValidationError):
                WebsiteSaleController.shop_payment_validate()

    def test_validate_order_out_of_stock_zero_price(self):
        """
        An error should be raised if you try to validate an order for
        an out of stock product with 0 price
        """
        WebsiteSaleController = WebsiteSale()
        storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'sale_ok': True,
            'is_storable': True,
            'website_published': True,
            'allow_out_of_stock_order': False,
            'lst_price': 0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': storable_product.id,
                'product_uom_qty': 12.0,
            })],
            'carrier_id': self.free_delivery.id,
        })
        self.free_delivery.write({'website_published': True})
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': storable_product.id,
            'inventory_quantity': 10.0,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
        }).action_apply_inventory()

        with MockRequest(self.env, website=self.website):
            request.cart = sale_order
            with self.assertRaises(ValidationError):
                WebsiteSaleController.shop_payment_validate()
