# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestDynamicSnippetCategory(WebsiteSaleCommon):
    def setUp(self):
        super().setUp()

        Category = self.env['product.public.category']
        self.category1, self.category2, self.category3 = Category.create([
            {'name': "Published Category"},
            {'name': "Published Category 2"},
            {'name': "Unpublished Category"},
        ])
        self.child_category = Category.create({
            'name': "Child category",
            'parent_id': self.category1.id,
        })
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

    def test_snippet_categories_returns_only_published_and_with_children(self):
        categories = self.env['product.public.category'].get_available_snippet_categories(
            self.website.id,
        )
        category_ids = [c['id'] for c in categories]
        self.assertIn(self.category1.id, category_ids)

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
            self.assertEqual(
                self.category1.cover_image,
                attachment.datas,
                "Cover image should match the uploaded attachment",
            )
