# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

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
