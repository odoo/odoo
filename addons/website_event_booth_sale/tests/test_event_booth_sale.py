from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.tests.common import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteEventBoothSale(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["website"].sudo().search(
            []
        ).show_line_subtotals_tax_selection = "tax_included"
        cls.tax = (
            cls.env["account.tax"]
            .sudo()
            .create(
                {
                    "name": "Tax 10",
                    "amount": 10,
                }
            )
        )
        cls.booth_product = cls.env["product.product"].create(
            {
                "name": "Test Booth Product",
                "description_sale": "Mighty Booth Description",
                "list_price": 20,
                "standard_price": 60.0,
                "taxes_id": [(6, 0, [cls.tax.id])],
                "type": "service",
                "service_tracking": "event_booth",
            }
        )
        cls.event_booth_category = cls.env["event.booth.category"].create(
            {
                "name": "Standard",
                "description": "<p>Standard</p>",
                "product_id": cls.booth_product.id,
                "price": 100.0,
            }
        )
        cls.event_type = cls.env["event.type"].create(
            {
                "name": "Booth Type",
                "event_type_booth_ids": [
                    Command.create(
                        {
                            "name": "Standard 1",
                            "booth_category_id": cls.event_booth_category.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Standard 2",
                            "booth_category_id": cls.event_booth_category.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Standard 3",
                            "booth_category_id": cls.event_booth_category.id,
                        }
                    ),
                ],
            }
        )
        cls.env["event.event"].create(
            {
                "name": "Test Event Booths",
                "event_type_id": cls.event_type.id,
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_published": True,
                "website_menu": True,
                "booth_menu": True,
            }
        )

    def test_tour(self):
        self.env["product.pricelist"].sudo().search([]).action_archive()
        self.partner_portal.write(
            {
                "street": "858 Lynn Street",
                "city": "Bayonne",
                "country_id": self.env.ref("base.state_us_25").id,
                "zip": "07002",
                "phone_ids": [
                    Command.clear(),
                    Command.create({"number": "(683)-556-5104"}),
                ],
            }
        )
        self.start_tour("/event", "website_event_booth_tour", login="portal")

    def test_booth_pricelists_different_currencies(self):
        self.env.ref("base.user_admin").partner_id.write(
            {
                "email": "mitchell.stephen@example.com",
                "name": "Mitchell Admin",
                "street": "215 Vine St",
                "city": "Scranton",
                "zip": "18503",
                "country_id": self.env.ref("base.us").id,
                "state_id": self.env.ref("base.state_us_39").id,
                "phone_ids": [
                    Command.clear(),
                    Command.create({"number": "+1 555-555-5555"}),
                ],
            }
        )
        self.start_tour(
            "/odoo", "event_booth_sale_pricelists_different_currencies", login="admin"
        )


@tagged("post_install", "-at_install")
class TestBoothCartLineRegistrations(TestWebsiteEventSaleCommon):
    """A cart line that already holds one booth must adopt the newly picked ones.

    `_cart_find_product_line` matches a line sharing ANY pending booth, so the
    second `_cart_add` is an UPDATE of the existing line rather than a new one,
    and `_prepare_order_line_update_values` is what carries the registrations.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.booth_product = cls.env["product.product"].create(
            {
                "name": "Booth Product",
                "list_price": 20.0,
                "type": "service",
                "service_tracking": "event_booth",
            }
        )
        cls.booth_category = cls.env["event.booth.category"].create(
            {
                "name": "Standard",
                "product_id": cls.booth_product.id,
                "price": 100.0,
            }
        )
        cls.event = cls.env["event.event"].create(
            {
                "name": "Booth Event",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "event_booth_ids": [
                    Command.create(
                        {"name": "Booth A", "booth_category_id": cls.booth_category.id}
                    ),
                    Command.create(
                        {"name": "Booth B", "booth_category_id": cls.booth_category.id}
                    ),
                ],
            }
        )
        cls.booth_a, cls.booth_b = cls.event.event_booth_ids

    def test_second_booth_reaches_the_existing_cart_line(self):
        registration_values = {
            "partner_id": self.partner.id,
            "contact_name": self.partner.name,
            "contact_email": "booth@example.com",
        }
        cart = self.empty_cart
        cart._cart_add(
            product_id=self.booth_product.id,
            quantity=1,
            event_booth_pending_ids=self.booth_a.ids,
            registration_values=registration_values,
        )
        line = cart.line_ids
        self.assertEqual(
            line.event_booth_registration_ids.event_booth_id,
            self.booth_a,
            "the first add registers the booth it was given",
        )

        cart._cart_add(
            product_id=self.booth_product.id,
            quantity=1,
            event_booth_pending_ids=(self.booth_a + self.booth_b).ids,
            registration_values=registration_values,
        )

        self.assertEqual(
            cart.line_ids,
            line,
            "a line sharing a pending booth is updated, not duplicated",
        )
        self.assertEqual(
            line.event_booth_registration_ids.event_booth_id,
            self.booth_a + self.booth_b,
            "the update must carry the registrations -- returning nothing from "
            "_prepare_order_line_update_values drops the newly picked booth silently",
        )
