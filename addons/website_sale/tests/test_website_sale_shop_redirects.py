# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.controllers.main import SHOP_PATH
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleShopRedirects(HttpCase, WebsiteSaleCommon):

    def test_website_sale_shop_redirects(self):
        category_a = self.env['product.public.category'].create({'name': "Category A"})
        category_b = self.env['product.public.category'].create({'name': "Category B"})
        test_product = self.env['product.template'].create({
            'name': "Test product",
            'public_categ_ids': [Command.link(category_a.id)],
            'website_published': True,
        })
        # Add a different published product to category B so that it is accessible to public users
        self._create_product(website_published=True, public_categ_ids=[Command.link(category_b.id)])

        slug = self.env['ir.http']._slug

        response = self.url_open(
            f'/shop?category={category_a.id}&some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/category/{slug(category_a)}?some-key=some-value',
        )

        response = self.url_open(
            f'/shop/product/{slug(test_product)}?category={category_a.id}&some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/{slug(category_a)}/{slug(test_product)}?some-key=some-value',
        )

        response = self.url_open(
            f'/shop/product/{slug(test_product)}?category=test&some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/{slug(test_product)}?some-key=some-value'
        )

        response = self.url_open(
            f'/shop/{slug(category_b)}/{slug(test_product)}?some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/{slug(test_product)}?some-key=some-value',
        )

    def test_ecommerce_product_page_url_unpublished_product(self):
        # Unpublished products should be hidden and return a 404.
        accessory_product = self.env['product.template'].create({
            'name': 'Access Product',
            'is_published': False,
        })
        url = f'{SHOP_PATH}/{accessory_product.id}'
        res = self.url_open(url)
        self.assertEqual(len(res.history), 0, "Unpublished products shouldn't redirect.")
        self.assertURLEqual(res.url, url, "Unpublished products shouldn't slug the URL.")
        self.assertEqual(res.status_code, 404, "Unpublished products should return a 404 page.")

    def test_ecommerce_category_page_url_invalid_category(self):
        # Invalid category should return a 404.
        url = f'{SHOP_PATH}/category/999999'
        res = self.url_open(url)

        self.assertEqual(res.status_code, 404, "Invalid category should return a 404.")

    def test_ecommerce_product_page_url_invalid_category(self):
        # Invalid category should redirect to the canonical product page.
        accessory_product = self.env['product.template'].create({
            'name': 'Access Product',
            'is_published': True,
        })
        url = f'{SHOP_PATH}/999999/{accessory_product.id}'
        res = self.url_open(url)

        self.assertEqual(
            len(res.history),
            1,
            "Invalid category with valid product should only redirect once to the product page.",
        )
        self.assertEqual(
            res.history[0].status_code,
            303,
            "Invalid category with valid product should redirect to the product page.",
        )
        good_url = f'{SHOP_PATH}/{self.env["ir.http"]._slug(accessory_product)}'
        self.assertURLEqual(res.url, good_url)

    def test_ecommerce_category_page_url_unpublished_product(self):
        # Unpublished product should redirect to the canonical category page (if category provided).
        category = self.env['product.public.category'].create({
            'name': 'Test Category',
        })
        # Add a different published product to category so that it is accessible to public users
        self.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'public_categ_ids': [
                Command.link(category.id),
            ],
        })
        accessory_product = self.env['product.template'].create({
            'name': 'Access Product',
            'public_categ_ids': [
                Command.link(category.id),
            ],
        })
        accessory_product.is_published = False
        url = f'{SHOP_PATH}/{category.id}/{accessory_product.id}'
        res = self.url_open(url)

        self.assertEqual(
            len(res.history),
            1,
            "Unpublished product with valid category should only redirect once to the category page.",
        )
        self.assertEqual(
            res.history[0].status_code,
            303,
            "Unpublished product with valid category should redirect to the category page.",
        )
        good_url = f'{SHOP_PATH}/category/{self.env["ir.http"]._slug(category)}'
        self.assertURLEqual(res.url, good_url)
