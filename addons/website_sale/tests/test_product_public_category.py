# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductPublicCategory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_multi(vals_list):
            return list(map(Command.create, vals_list))

        cls.published_product, cls.unpublished_product = cls.env["product.template"].create([
            {"name": "Published Product", "is_published": True},
            {"name": "Unpublished Product", "is_published": False},
        ])

        cls.env["product.public.category"].search([]).unlink()

        cls.categories = cls.env["product.public.category"].create([
            {
                "name": "1",
                "child_id": create_multi([
                    {"name": "1.1", "child_id": create_multi([{"name": "1.1.1"}])},
                    {"name": "1.2", "product_tmpl_ids": [Command.link(cls.published_product.id)]},
                ]),
            },
            {
                "name": "2",
                "child_id": create_multi([
                    {
                        "name": "2.1",
                        "child_id": create_multi([
                            {
                                "name": "2.1.1",
                                "product_tmpl_ids": [
                                    Command.link(cls.published_product.id),
                                    Command.link(cls.unpublished_product.id),
                                ],
                            }
                        ]),
                    },
                    {"name": "2.2"},
                ]),
            },
            {"name": "3", "product_tmpl_ids": [Command.link(cls.unpublished_product.id)]},
        ])

    def test_search_has_published_products(self):
        published_categs = set(
            self
            .env["product.public.category"]
            .search([("has_published_products", "not in", (False,))])
            .mapped("name")
        )

        self.assertSetEqual(published_categs, {"1", "1.2", "2", "2.1", "2.1.1"})

    def test_search_does_not_have_published_products(self):
        unpublished_categs = set(
            self
            .env["product.public.category"]
            .search([("has_published_products", "!=", True)])
            .mapped("name")
        )

        self.assertSetEqual(unpublished_categs, {"1.1", "1.1.1", "2.2", "3"})

    def test_compute_website_url_mixed_access(self):
        public_user = self.env.ref('base.public_user')
        categories = (self.categories[0] + self.categories[0].child_id).with_user(public_user)

        categories[0].check_access('read')
        with self.assertRaises(AccessError):
            categories[1].check_access('read')
        categories[2].check_access('read')
        # prefetch as public user
        categories[0].website_url
        self.assertRecordValues(categories.sudo(), [
            {'website_url': f'/shop/category/1-{categories[0].id}'},
            {'website_url': '#'},
            {'website_url': f'/shop/category/1-{categories[0].id}/1-2-{categories[2].id}'},
        ])
