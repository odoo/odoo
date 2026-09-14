from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestWishlistProcess(HttpCase):
    def test_01_wishlist_tour(self):
        self.env["product.template"].search([]).write({"website_published": False})
        attributes = self.env["product.attribute"].create(
            [
                {
                    "name": "Legs",
                    "sequence": 10,
                    "value_ids": [
                        Command.create(
                            {
                                "name": "Steel",
                                "sequence": 1,
                            }
                        ),
                        Command.create(
                            {
                                "name": "Aluminium",
                                "sequence": 2,
                            }
                        ),
                    ],
                },
                {
                    "name": "Color",
                    "sequence": 20,
                    "value_ids": [
                        Command.create(
                            {
                                "name": "White",
                                "sequence": 1,
                            }
                        ),
                        Command.create(
                            {
                                "name": "Black",
                                "sequence": 2,
                            }
                        ),
                    ],
                },
            ]
        )

        self.env["product.template"].create(
            {
                "name": "Customizable Desk (TEST)",
                "standard_price": 500.0,
                "list_price": 750.0,
                "website_published": True,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(attribute.value_ids.ids)],
                        }
                    )
                    for attribute in attributes
                ],
            }
        )

        self.env.ref("base.user_admin").name = "Mitchell Admin"

        self.start_tour("/", "shop_wishlist", timeout=120)


@tagged("-at_install", "post_install")
class TestWishlistPublicUsers(HttpCase):
    def test_a_public_group_user_that_is_not_the_website_visitor_sees_a_session_wishlist(
        self,
    ):
        # the header renders the wish count for every visitor; a user of the
        # public group that is not the website's own public user has no read
        # access on wishlists, and reading his own was a 403 on every page
        # (a 404 page included)
        visitor = self.env["res.users"].create(
            {
                "name": "other public",
                "login": "other_public",
                "password": "other_public",
                "group_ids": [Command.set([self.env.ref("base.group_public").id])],
            }
        )
        self.authenticate(visitor.login, visitor.login)
        response = self.url_open("/no-such-page-for-the-wishlist-header")
        self.assertEqual(response.status_code, 404)
        self.assertIn("o_wsale_my_wish", response.text)
