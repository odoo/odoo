# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo import Command
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


class TestDynamicSnippetCategory(WebsiteSaleCommon):
    def setUp(self):
        super().setUp()

        Category = self.env['product.public.category']
        # Create a test product public category
        self.category1 = Category.create({'name': "Published Category"})
        self.category2 = Category.create({'name': "Published Category 2"})
        self.child_category = Category.create({
            'name': "Child category",
            'parent_id': self.category1.id,
        })
        self.category3 = Category.create({'name': "Unpublished Category"})
        self.env['product.template'].create({
            'name': "Test Product",
            'public_categ_ids': [
                Command.link(self.category1.id),
                Command.link(self.category2.id),
                Command.link(self.child_category.id),
            ],
            'website_published': True,
        })
        self.website_sale = WebsiteSale()
        self.website = self.website.with_user(self.env.ref('base.user_admin'))

    def test_get_shop_categories(self):
        """Test that published categories are returned by the _get_shop_categories"""
        with MockRequest(self.website.env, website=self.website):
            categories = self.website_sale.get_shop_categories()
            root = [html.fromstring(category) for category in categories]
            self.assertEqual(
                self.category1.id,
                int(root[0].attrib.get('data-category-id')),
                "Only published categories should be returned",
            )
            self.assertEqual(
                self.category2.id,
                int(root[1].attrib.get('data-category-id')),
                "Only published categories should be returned",
            )
            categories = self.website_sale.get_shop_categories(self.category1.id)
            root = [html.fromstring(category) for category in categories]
            self.assertEqual(
                self.child_category.id,
                int(root[0].attrib.get('data-category-id')),
                "only children categories of category1 should be returned",
            )

    def test_get_snippet_categories(self):
        """Test that snippet categories have cover images"""
        categories = self.env['product.public.category'].get_snippet_categories(self.website.id)
        self.assertEqual(
            self.category1.id,
            categories[0]['id'],
            "Only published categories should be returned",
        )
        self.assertEqual(
            self.category2.id,
            categories[1]['id'],
            "Only published categories should be returned",
        )

    def test_set_category_image(self):
        """Test setting a cover image via JSON-RPC route"""
        attachment = self.env['ir.attachment'].create({
            'name': "test.png",
            'datas': 'iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAJElEQVQI'
                     'mWP4/b/qPzbM8Pt/1X8GBgaEAJTNgFcHXqOQMV4dAMmObXXo1/BqAAAA'
                     'AElFTkSuQmCC',
            'public': True,
        })
        with MockRequest(self.website.env, website=self.website):
            self.website_sale.set_category_image(self.category1.id, attachment.id)
            self.assertTrue(
                self.category1.cover_image,
                "Cover image should be set on the category",
            )
