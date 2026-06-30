# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestEcommerceAccess(HttpCaseWithUserDemo, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.filled_category, cls.empty_category = cls.env['product.public.category'].create([
            {'name': 'Category with Product', 'website_id': cls.website.id},
            {'name': 'Empty Category', 'website_id': cls.website.id},
        ])

        cls.env['product.public.category'].create([
            {
                'name': 'Has Products',
                'parent_id': cls.filled_category.id,
                'website_id': cls.website.id,
            },
            {
                'name': 'Empty Subcategory',
                'parent_id': cls.filled_category.id,
                'website_id': cls.website.id,
            },
            {
                'name': 'Empty Subcategory of Empty Category',
                'parent_id': cls.empty_category.id,
                'website_id': cls.website.id,
            },
        ])

        # Add one dummy product in one of the subcategories
        cls._create_product(public_categ_ids=[cls.filled_category.child_id[0].id])

    def test_ecommerce_access_public_user(self):
        # By default, everyone has access to ecommerce
        self.assertTrue(self.website.with_user(self.public_user).has_ecommerce_access())
        self.website.ecommerce_access = 'logged_in'
        self.assertFalse(self.website.with_user(self.public_user).has_ecommerce_access())

    def test_frontend_ecommerce_access_public_user(self):
        """
        Ensures that the '/shop' URL returns a 200 OK status code even if categories are empty when
        not logged.
        """
        self.quick_ref('website_sale.products_categories').active = True
        self.quick_ref('website_sale.option_collapse_products_categories').active = False

        response = self.url_open('/shop')
        self.assertEqual(response.status_code, 200)  # Check that customers can access

    def test_ecommerce_access_logged_user(self):
        # By default, everyone has access to the ecommerce
        self.assertTrue(self.website.has_ecommerce_access())
        self.website.ecommerce_access = 'logged_in'
        # Check if logged-in users still have access to ecommerce after restricting it
        self.assertTrue(self.website.has_ecommerce_access())

    def test_frontend_ecommerce_access_portal_user(self):
        """
        Ensures that the '/shop' URL returns a 200 OK status code even if categories are empty when
        logged as portal user.
        """
        self.quick_ref('website_sale.products_categories').active = True
        self.quick_ref('website_sale.option_collapse_products_categories').active = False
        portal_user = self._create_new_portal_user(website_id=self.website.id)

        self.authenticate(portal_user.login, portal_user.login)
        response = self.url_open('/shop')
        self.assertEqual(response.status_code, 200)  # Check that customers can access

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

    def test_ecommerce_access_shop_redirection(self):
        self.website.ecommerce_access = 'logged_in'
        self.authenticate(None, None)
        public_category = self.env['product.public.category'].create({
            'name': 'Test Category',
        })
        public_product_template = self.env['product.template'].create({
            'name': 'Test Template',
            'public_categ_ids': [public_category.id],
            'website_published': True,
        })
        category_slug = self.env["ir.http"]._slug(public_category)
        response = self.url_open(f'/shop/category/{category_slug}/page/1', allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, f'/web/login?redirect=/shop/category/{category_slug}/page/1')

        product_slug = self.env["ir.http"]._slug(public_product_template)
        response = self.url_open(f'/shop/{product_slug}', allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertURLEqual(response.url, f'/web/login?redirect=/shop/{product_slug}')
