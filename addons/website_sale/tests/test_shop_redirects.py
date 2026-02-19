# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.controllers.main import SHOP_PATH
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleShopRedirects(HttpCase, WebsiteSaleCommon):

    def test_website_sale_shop_redirects(self):
        test_category = self.env['product.public.category'].create({'name': "Test category"})
        test_product = self.env['product.template'].create({
            'name': "Test product",
            'public_categ_ids': [Command.link(test_category.id)],
            'website_published': True,
        })

        slug = self.env['ir.http']._slug

        response = self.url_open(
            f'/shop?category={test_category.id}&some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/category/{slug(test_category)}?some-key=some-value',
        )

        response = self.url_open(
            f'/shop/{slug(test_product)}?category={test_category.id}&some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/product/{slug(test_product)}?some-key=some-value',
        )

        response = self.url_open(
            f'/shop/{slug(test_category)}/{slug(test_product)}?some-key=some-value',
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertURLEqual(
            response.headers.get('Location'),
            f'/shop/product/{slug(test_product)}?some-key=some-value',
        )

    def test_ecommerce_product_page_url_unpublished_product(self):
        # Unpublished products should be hidden and return a 404.
        accessory_product = self.env['product.template'].create({
            'name': 'Access Product',
            'is_published': False,
        })
        url = f'{SHOP_PATH}/product/{accessory_product.id}'
        res = self.url_open(url)
        self.assertEqual(len(res.history), 0, "Unpublished products shouldn't redirect.")
        self.assertURLEqual(res.url, url, "Unpublished products shouldn't slug the URL.")
        self.assertEqual(res.status_code, 404, "Unpublished products should return a 404 page.")

    def test_ecommerce_category_page_url_invalid_category(self):
        # Invalid category should return a 404.
        url = f'{SHOP_PATH}/category/999999'
        res = self.url_open(url)

        self.assertEqual(res.status_code, 404, "Invalid category should return a 404.")
