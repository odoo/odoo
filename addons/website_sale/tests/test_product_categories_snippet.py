# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestProductCategoriesSnippet(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["product.public.category"]
        cls.computers, cls.hidden = Category.create([{"name": "Computers"}, {"name": "Hidden"}])
        cls.laptops, cls.tablets, cls.hidden_computers = Category.create([
            {"name": "Laptops", "parent_id": cls.computers.id},
            {"name": "Tablets", "parent_id": cls.computers.id},
            {"name": "Hidden computers", "parent_id": cls.computers.id},
        ])
        cls.env["product.template"].create({
            "name": "Laptop",
            "public_categ_ids": [
                Command.link(cls.computers.id),
                Command.link(cls.laptops.id),
                Command.link(cls.tablets.id),
            ],
            "website_published": True,
        })

    def test_visitors_only_get_categories_with_published_products(self):
        categories_data = (
            self
            .env["product.public.category"]
            .with_user(self.env.ref("base.public_user"))
            .with_context(website_id=self.website.id)
            ._prepare_product_categories_snippet_data((self.computers | self.hidden).ids)
        )
        self.assertEqual(
            {
                category_id: [child["id"] for child in category_data["child_categories"]]
                for category_id, category_data in categories_data.items()
            },
            {self.computers.id: (self.laptops | self.tablets).ids},
        )


@tagged("post_install", "-at_install")
class TestProductCategoriesSnippetUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["product.public.category"]
        cls.parent = Category.create({"name": "Tour Parent"})
        cls.child = Category.create({"name": "Tour Child", "parent_id": cls.parent.id})
        cls.env["product.template"].create({
            "name": "Tour Product",
            "public_categ_ids": [Command.link(cls.parent.id), Command.link(cls.child.id)],
            "website_published": True,
        })

    def test_mega_menu_lists_categories_that_can_be_renamed_from_the_editor(self):
        self.start_tour(
            self.env["website"].get_client_action_url("/", True),
            "mega_menu_product_categories",
            login="admin",
        )
