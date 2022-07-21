# coding: utf-8

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class WebsiteSaleCart(TransactionCase):

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

    def test_update_pricelist_with_invalid_product(self):
        product = self.env['product.product'].create({
            'name': 'Test Product',
        })

        # Should not raise an exception
        website = self.website.with_user(self.public_user)
        with MockRequest(product.with_user(self.public_user).env, website=website):
            order = website.sale_get_order(force_create=True)
            order.write({
                'order_line': [(0, 0, {
                    'product_id': product.id,
                })]
            })
            website.sale_get_order(update_pricelist=True)
