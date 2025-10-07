# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_sale.controllers.cart import Cart as CartController
from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockDeliveryController(WebsiteSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storable_product = cls._create_product()
        cls._add_product_qty_to_wh(cls.storable_product.id, 10.0, cls.warehouse.lot_stock_id.id)

        cls.CheckoutController = CheckoutController()
        cls.CartController = CartController()

    def test_validate_payment_with_no_available_delivery_method(self):
        """
        An error should be raised if you try to validate an order with a storable
        product without any delivery method available
        """
        self.env['delivery.carrier'].search([]).write({'website_published': False})
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, path='/shop/cart/add') as request:
            self.CartController.add_to_cart(
                product_template_id=self.storable_product.product_tmpl_id,
                product_id=self.storable_product.id,
                quantity=1,
            )
            cart = request.cart
            self.assertTrue(cart.order_line)

        with MockRequest(
            website.env, website=website, path='/shop/address/submit', sale_order_id=cart.id,
        ) as request:
            self.CheckoutController.shop_address_submit(
                address_type='delivery',
                use_delivery_as_billing=True,
                name='Test partner',
                **self.dummy_partner_address_values,
            )
            self.assertNotEqual(request.cart.partner_id, self.public_partner)

        with (
            MockRequest(
                website.env, website=website, path='/shop/payment/validate', sale_order_id=cart.id,
            ),
            self.assertRaises(ValidationError),
        ):
            # Attempt to validate the payment a little too quickly
            self.CheckoutController.shop_payment_validate()

    def test_validate_order_out_of_stock_zero_price(self):
        """
        An error should be raised if you try to validate an order for
        an out of stock product with 0 price
        """
        self.storable_product.lst_price = 0.0
        cart = self._create_so(
            order_line=[Command.create({
                'product_id': self.storable_product.id,
                'product_uom_qty': 12.0,
            })],
            carrier_id=self.free_delivery.id,
        )

        website = self.website.with_user(self.public_user)
        with (
            MockRequest(
                website.env, website=website, path='/shop/payment/validate', sale_order_id=cart.id,
            ),
            self.assertRaises(ValidationError),
        ):
            self.CheckoutController.shop_payment_validate()
