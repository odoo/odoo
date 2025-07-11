# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('only_this_class', 'post_install', '-at_install')
class TestEcommerceAccess(HttpCaseWithUserDemo, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.productCategory = cls.env['product.public.category'].create(
            {'name': 'Category with Product', 'website_id': cls.website.id},
        )
        cls.emptyCategory = cls.env['product.public.category'].create(
            {'name': 'Empty Category', 'website_id': cls.website.id},
        )

        cls.env['product.public.category'].create([
            {
                'name': 'Has Products',
                'parent_id': cls.productCategory.id,
                'website_id': cls.website.id,
            },
            {
                'name': 'Empty Subcategory',
                'parent_id': cls.productCategory.id,
                'website_id': cls.website.id,
            },
            {
                'name': 'Empty Subcategory of Empty Category',
                'parent_id': cls.emptyCategory.id,
                'website_id': cls.website.id,
            },
        ])

        # Add one dummy product in one of the subcategories
        cls.product_a = cls._create_product(
            public_categ_ids=[cls.productCategory.child_id[0].id],
            is_published=True,
        )

        cls.quick_ref('website_sale.products_categories').active = True
        cls.quick_ref('website_sale.option_collapse_products_categories').active = False
        cls.portal_user = cls._create_new_portal_user(website_id=cls.website.id)

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

    def test_ecommerce_public_user_access_when_empty_categories(self):
        """
        Ensures that the '/shop' URL returns a 200 OK status code even if categories are empty
        when not logged.
        """
        response = self.url_open('/shop')
        self.assertEqual(response.status_code, 200)

    def test_ecommerce_portal_user_access_when_empty_categories(self):
        """
        Ensures that the '/shop' URL returns a 200 OK status code even if categories are empty
        when logged as portal user.
        """
        self.authenticate(self.portal_user.login, self.portal_user.login)
        response = self.url_open('/shop')
        self.assertEqual(response.status_code, 200)
