# coding: utf-8

from unittest.mock import patch

from odoo.addons.base.tests.common import TransactionCaseWithUserPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale, PaymentPortal
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.models.product_template import ProductTemplate
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.fields import Command


@tagged('post_install', '-at_install')
class WebsiteSaleCart(TransactionCaseWithUserPortal):

    @classmethod
    def setUpClass(cls):
        super(WebsiteSaleCart, cls).setUpClass()
        cls.website = cls.env['website'].browse(1)
        cls.WebsiteSaleController = WebsiteSale()
        cls.public_user = cls.env.ref('base.public_user')

    def test_add_cart_deleted_product(self):
        # Create a published product then unlink it
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
        })
        product_id = product.id
        product.unlink()

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product_id, add_qty=1)

    def test_add_cart_unpublished_product(self):
        # Try to add an unpublished product
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
        })

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)

        # public but remove sale_ok
        product.sale_ok = False
        product.website_published = True

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)

    def test_add_cart_archived_product(self):
        # Try to add an archived product
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
        })
        product.active = False

        with self.assertRaises(UserError):
            with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
                self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)

    def test_zero_price_product_rule(self):
        """
        With the `prevent_zero_price_sale` that we have on website, we can't add free products
        to our cart.
        There is an exception for certain product types specified by the
        `_get_product_types_allow_zero_price` method, so this test ensures that it works
        by mocking that function to return the "service" product type.
        """
        website_prevent_zero_price = self.env['website'].create({
            'name': 'Prevent zero price sale',
            'prevent_zero_price_sale': True,
        })
        product_consu = self.env['product.product'].create({
            'name': 'Cannot be zero price',
            'detailed_type': 'consu',
            'list_price': 0,
            'website_published': True,
        })
        product_service = self.env['product.product'].create({
            'name': 'Can be zero price',
            'detailed_type': 'service',
            'list_price': 0,
            'website_published': True,
        })

        with patch.object(ProductTemplate, '_get_product_types_allow_zero_price', lambda pt: ['service']):
            with self.assertRaises(UserError, msg="'consu' product type is not allowed to have a 0 price sale"), \
                 MockRequest(self.env, website=website_prevent_zero_price):
                self.WebsiteSaleController.cart_update_json(product_id=product_consu.id, add_qty=1)

            # service types should not raise a UserError
            with MockRequest(self.env, website=website_prevent_zero_price):
                self.WebsiteSaleController.cart_update_json(product_id=product_service.id, add_qty=1)

    def test_update_cart_before_payment(self):
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })
        website = self.website.with_user(self.public_user)
        with MockRequest(product.with_user(self.public_user).env, website=website):
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
            sale_order.access_token = 'test_token'
            old_amount = sale_order.amount_total
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            # Try processing payment with the old amount
            with self.assertRaises(UserError):
                PaymentPortal().shop_payment_transaction(sale_order.id, sale_order.access_token, amount=old_amount)

    def test_update_cart_zero_qty(self):
        # Try to remove a product that has already been removed
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })
        portal_user = self.user_portal
        website = self.website.with_user(portal_user)

        SaleOrderLine = self.env['sale.order.line']

        with MockRequest(product.with_user(portal_user).env, website=website):
            # add the product to the cart
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
            self.assertEqual(sale_order.amount_untaxed, 1000.0)

            # remove the product from the cart
            self.WebsiteSaleController.cart_update_json(product_id=product.id, line_id=sale_order.order_line.id, set_qty=0)
            self.assertEqual(sale_order.amount_total, 0.0)
            self.assertEqual(sale_order.order_line, SaleOrderLine)

            # removing the product again doesn't add a line with zero quantity
            self.WebsiteSaleController.cart_update_json(product_id=product.id, set_qty=0)
            self.assertEqual(sale_order.order_line, SaleOrderLine)

            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=0)
            self.assertEqual(sale_order.order_line, SaleOrderLine)

    def test_unpublished_accessory_product_visibility(self):
        # Check if unpublished product is shown to public user
        accessory_product = self.env['product.product'].create({
            'name': 'Access Product',
            'is_published': False,
        })

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'accessory_product_ids': [Command.link(accessory_product.id)]
        })

        website = self.website.with_user(self.public_user)
        with MockRequest(product.with_user(self.public_user).env, website=self.website.with_user(self.public_user)):
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
            self.assertEqual(len(sale_order._cart_accessories()), 0)
