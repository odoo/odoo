# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestEcommerceAccess(HttpCaseWithUserDemo, WebsiteSaleCommon):

    def test_ecommerce_access_public_user(self):
        # By default, everyone has access to ecommerce
        self.assertTrue(self.website.with_user(self.public_user).has_ecommerce_access())
        self.website.ecommerce_access = 'logged_in'
        self.assertFalse(self.website.with_user(self.public_user).has_ecommerce_access())

    def test_ecommerce_access_logged_user(self):
        # By default, everyone has access to the ecommerce
        self.assertTrue(self.website.has_ecommerce_access())
        self.website.ecommerce_access = 'logged_in'
        # Check if logged-in users still have access to ecommerce after restricting it
        self.assertTrue(self.website.has_ecommerce_access())

    def test_ecommerce_menu_visibility_public_user(self):
        self.menu = self.env['website.menu'].create({
            'name': 'Shop',
            'url': '/shop',
            'parent_id': self.website.menu_id.id,
            'sequence': 0,
            'website_id': self.website.id,
        })

        # Check if by default public user can see shop menu
        self.menu.with_user(self.public_user).sudo()._compute_visible()  # Needs to be sudoed as
        # public user can't access _compute_visible
        self.assertTrue(self.menu.is_visible)

        self.website.ecommerce_access = 'logged_in'
        self.menu.with_user(self.public_user).sudo()._compute_visible()
        # Check if menu is hidden for public user when ecommerce is restricted
        self.assertFalse(self.menu.is_visible)

    def test_ecommerce_access_shop_cart_redirection(self):
        self.website.ecommerce_access = 'logged_in'
        self.authenticate(None, None)
        response = self.url_open('/shop/cart', allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, '/web/login?redirect=/shop/cart')

        public_category = self.env['product.public.category'].create({
            'name': 'Test Category',
        })
        category_slug = self.env["ir.http"]._slug(public_category)
        response = self.url_open(f'/shop/category/{category_slug}/page/1', allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, f'/web/login?redirect=/shop/category/{category_slug}/page/1')

        public_product_template = self.env['product.template'].create({
            'name': 'Test Template',
            'website_published': True
        })
        product_slug = self.env["ir.http"]._slug(public_product_template)
        response = self.url_open(f'/shop/{product_slug}', allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, f'/web/login?redirect=/shop/{product_slug}')
