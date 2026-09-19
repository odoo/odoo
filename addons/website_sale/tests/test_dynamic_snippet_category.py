# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestDynamicSnippetCategory(WebsiteSaleCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    def setUp(self):
        super().setUp()

        Category = self.env["product.public.category"]
        self.category1, self.category2, self.category3 = Category.create([
            {"name": "Published Category"},
            {"name": "Published Category 2"},
            {"name": "Unpublished Category"},
        ])
        self.child_category = Category.create({
            "name": "Child category",
            "parent_id": self.category1.id,
        })
        self.env["product.template"].create({
            "name": "Test Product",
            "public_categ_ids": [
                Command.link(self.category1.id),
                Command.link(self.category2.id),
                Command.link(self.child_category.id),
            ],
            "website_published": True,
        })
        self.website_sale = WebsiteSale()
        self.website = self.website.with_user(self.env.ref("base.user_admin"))

    def test_snippet_categories_sample(self):
        sample = self.env.ref("website_sale.dynamic_filter_category_list").sudo()._prepare_sample(7)
        self.assertEqual(len(sample), 7)
        for category in sample:
            self.assertTrue(category["cover_image"].startswith("/website_sale/static/src/img/"))

    def test_snippet_categories_returns_only_published_and_with_children(self):
        categories = self.env["product.public.category"].get_available_snippet_categories(
            self.website.id
        )
        category_ids = [c["id"] for c in categories]
        self.assertIn(self.category1.id, category_ids)

    def test_visitor_does_not_see_categories_without_published_products(self):
        SnippetFilter = self.env["website.snippet.filter"].with_user(self.public_user)
        with self.mock_request(user=self.public_user, website=self.website):
            categories = SnippetFilter._prepare_category_list_data()
        self.assertNotIn(
            self.category3.id,
            [category["id"] for category in categories],
            "A category without published products should be hidden from visitors",
        )

    def test_designer_sees_categories_without_published_products_as_unpublished(self):
        designer = self.env.ref("base.user_admin")
        SnippetFilter = self.env["website.snippet.filter"].with_user(designer)
        with self.mock_request(user=designer, website=self.website):
            categories = SnippetFilter._prepare_category_list_data()
        self.assertTrue(
            next(c for c in categories if c["id"] == self.category3.id)["unpublished"],
            "A category without published products should be flagged for the designer",
        )

    def test_categories_of_other_websites_are_excluded(self):
        other_website = self.env["website"].sudo().create({"name": "Other Website"})
        other_category = (
            self
            .env["product.public.category"]
            .sudo()
            .create({"name": "Other Website Category", "website_id": other_website.id})
        )
        designer = self.env.ref("base.user_admin")
        SnippetFilter = self.env["website.snippet.filter"].with_user(designer)
        with self.mock_request(user=designer, website=self.website):
            categories = SnippetFilter._prepare_category_list_data()
        self.assertNotIn(
            other_category.id,
            [category["id"] for category in categories],
            "A category bound to another website should not be listed",
        )

    def test_filtering_on_a_category_lists_it_before_its_children(self):
        designer = self.env.ref("base.user_admin")
        SnippetFilter = self.env["website.snippet.filter"].with_user(designer)
        with self.mock_request(user=designer, website=self.website):
            categories = SnippetFilter._prepare_category_list_data(parent_id=self.category1.id)
        self.assertEqual(
            categories[0]["id"],
            self.category1.id,
            "The filtered category should be listed before its children",
        )

    def test_categories_without_children_are_not_offered_as_filters(self):
        categories = self.env["product.public.category"].get_available_snippet_categories(
            self.website.id
        )
        self.assertNotIn(
            self.category2.id,
            [category["id"] for category in categories],
            "A category without children cannot be used as a filter",
        )

    def test_set_category_image(self):
        """Test setting a cover image via JSON-RPC route."""
        attachment = self.env["ir.attachment"].create({
            "name": "test.png",
            "raw": "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAJElEQVQI"
            "mWP4/b/qPzbM8Pt/1X8GBgaEAJTNgFcHXqOQMV4dAMmObXXo1/BqAAAA"
            "AElFTkSuQmCC",
            "public": True,
        })
        with self.mock_request(user=self.env.user):
            self.website_sale.set_category_image(self.category1.id, attachment.id)
            self.assertEqual(
                self.category1.cover_image.content,
                attachment.raw.content,
                "Cover image should match the uploaded attachment",
            )
