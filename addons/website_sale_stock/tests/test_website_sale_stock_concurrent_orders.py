# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import closing

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_stock.controllers.main import PaymentPortal


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockConcurrentOrders(PaymentCommon):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.Controller = PaymentPortal()

    def test_website_sale_stock_out_of_stock_products(self):
        limited_product = self.env['product.product'].search([('name', 'ilike', 'Limited Product')])
        if not limited_product:
            self.skipTest('Cannot test concurrent transactions without demo data.')
        default_transaction_values = {
            'payment_method_id': self.payment_method_id,
            'amount': 5.75,
            'provider_id': self.provider.id,
            'flow': 'redirect',
            'token_id': None,
            'tokenization_requested': False,
            'landing_route': 'stub',
        }
        # Open a new cursor to simulate a concurrent transaction locking limited_product's quants.
        with closing(self.registry.cursor()) as cr:
            cr.execute("SELECT id FROM stock_quant WHERE product_id = %s FOR NO KEY UPDATE", [limited_product.id])
            with MockRequest(self.env, website=self.website):
                sale_order = self.website.sale_get_order(force_create=True)
                sale_order.write({
                    'order_line': [Command.create({'product_id': limited_product.id, 'product_uom_qty': 5.0})],
                    'carrier_id': self.env.ref('delivery.free_delivery_carrier').id
                })
                # Try processing payment with another transaction locking the related quants.
                with self.assertRaisesRegex(ValidationError, "the cart contains products that are currently out of stock"):
                    self.Controller.shop_payment_transaction(sale_order.id, sale_order.access_token, **default_transaction_values)
