# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, HttpCase

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestDynamicSnippetCategory(WebsiteSaleCommon, HttpCase):
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
        self.test_attachment = self.env['ir.attachment'].create({
            'name': "test.png",
            'datas': 'iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAJElEQVQI'
                     'mWP4/b/qPzbM8Pt/1X8GBgaEAJTNgFcHXqOQMV4dAMmObXXo1/BqAAAA'
                     'AElFTkSuQmCC',
            'public': True,
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
        with MockRequest(self.website.env, website=self.website):
            self.website_sale.set_category_image(self.category1.id, self.test_attachment.id)
            self.assertEqual(
                self.category1.cover_image,
                self.test_attachment.datas,
                "Cover image should match the uploaded attachment",
            )

    def test_set_category_image_portal_user(self):
        res = self.url_open(
            '/snippets/category/set_image',
            data={'category_id': self.category1.id, 'attachment_id': self.test_attachment.id},
            method='POST',
        )
        self.assertEqual(
            res.status_code,
            415,
            "Portal users should not be able to set category images",
        )

    def test_prepare_category_list_data(self):
        """Test the data preparation for the category list"""
        with MockRequest(self.website.env, website=self.website):
            response = self.env['website.snippet.filter']._prepare_category_list_data()
            base_url = self.website.get_base_url()
            default_img_path = self.env['product.template']._get_product_placeholder_filename()
            default_img_url = f'{base_url}/{default_img_path}'
            expected_response = [{
                'id': self.category1.id,
                'name': "Published Category",
                'unpublished': not self.category1.has_published_products,
                'cover_image': default_img_url,
            }, {
                'id': self.category2.id,
                'name': "Published Category 2",
                'unpublished': not self.category2.has_published_products,
                'cover_image': default_img_url,
            }]
            for category in expected_response:
                self.assertIn(category, response)

            self.child_category.cover_image = self.test_attachment.datas
            response = self.env['website.snippet.filter']._prepare_category_list_data(
                parent_id=self.category1.id,
            )
            expected_response = [{
                'id': self.category1.id,
                'name': "Published Category",
                'unpublished': not self.category1.has_published_products,
                'cover_image': default_img_url,
            }, {
                'id': self.child_category.id,
                'name': "Child category",
                'unpublished': not self.child_category.has_published_products,
                'cover_image': f"""{base_url}{self.website.image_url(
                    self.child_category, 'cover_image',
                )}""",
            }]
            for category in expected_response:
                self.assertIn(category, response)
