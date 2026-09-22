from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.event_product.tests.common import TestEventProductCommon


@tagged("post_install", "-at_install")
class TestEventProduct(TestEventProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_event = cls.env["event.event"].create(
            {
                "name": "TestEventProduct",
                "event_type_id": cls.event_type_tickets.id,
            }
        )

    def test_ensure_event_service_tracking(self):
        with self.assertRaises(ValidationError):
            self.event_product.service_tracking = "no"
        with self.assertRaises(ValidationError):
            with Form(self.event_product) as product_form:
                product_form.type = "consu"

    def test_ensure_event_type_ticket_service_tracking(self):
        """A product with a mismatched service_tracking must be rejected on
        the event.type.ticket side too, not only via product.product."""
        other_product = self.env["product.product"].create(
            {
                "name": "Not An Event Product",
                "list_price": 5,
                "type": "service",
                "service_tracking": "no",
            }
        )
        ticket_type = self.event_type_tickets.event_type_ticket_ids[0]
        with self.assertRaises(ValidationError):
            ticket_type.product_id = other_product.id

    def test_price_reduce_taxinc_recomputes_on_dependency_change(self):
        """Regression test: price_reduce_taxinc must stay in sync with its
        declared dependencies (price_reduce, product_id, product_id.taxes_id)."""
        ticket = self.test_event.event_ticket_ids[0]
        # Clear any tax the product picked up from company defaults on
        # creation, so the "no tax" baseline below is actually tax-free.
        ticket.product_id.taxes_id = [(6, 0, [])]
        self.assertEqual(ticket.price_reduce_taxinc, ticket.price_reduce)

        tax = self.env["account.tax"].create(
            {
                "name": "Test Tax 25%",
                "amount": 25.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        ticket.product_id.taxes_id = [(6, 0, [tax.id])]

        self.assertAlmostEqual(
            ticket.price_reduce_taxinc,
            ticket.price_reduce * 1.25,
            msg="price_reduce_taxinc did not recompute after product_id.taxes_id changed",
        )

    def test_registration_status_defaults_without_order(self):
        """event.registration._compute_registration_status must default
        sale_status to 'free' and state to 'open' when _has_order() is False."""
        registration = self.env["event.registration"].create(
            {
                "event_id": self.test_event.id,
            }
        )
        self.assertEqual(registration.sale_status, "free")
        self.assertEqual(registration.state, "open")

    def test_price_incl_follows_the_event_company_currency(self):
        """price_incl applies the product's taxes and rounds in the event
        company's currency -- the tax jurisdiction's -- not the product's."""
        ticket = self.test_event.event_ticket_ids[0]
        ticket.product_id.taxes_id = [(6, 0, [])]
        ticket.price = 100.0
        self.assertEqual(ticket.price_incl, 100.0, "no tax means no uplift")

        tax = self.env["account.tax"].create(
            {
                "name": "Test Tax 25%",
                "amount": 25.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        ticket.product_id.taxes_id = [(6, 0, [tax.id])]
        self.assertAlmostEqual(ticket.price_incl, 125.0)
        self.assertEqual(
            ticket.currency_id,
            ticket.event_id.company_id.currency_id,
            "single-company setup: the two currencies coincide, so this test "
            "pins the value and test_tax_computes_share_one_currency pins the base",
        )

    def test_tax_computes_share_the_event_company_currency(self):
        """Both tax computes must round in the event company's currency, not the
        product's. The two diverge as soon as a product is shared across
        companies: product.currency_id falls back to the MAIN company's.

        Detected without a tax, by giving the event company a currency that
        rounds to whole units: a price of 100.4 comes back as 100.0 when the
        company's currency is the rounding base, and as 100.4 when the
        product's two-decimal currency is used instead.
        """
        chunky = self.env["res.currency"].create(
            {"name": "CHK", "symbol": "C", "rounding": 1.0, "decimal_places": 0}
        )
        other_company = self.env["res.company"].create(
            {"name": "Rounding Co", "currency_id": chunky.id}
        )
        shared_product = self.env["product.product"].create(
            {
                "name": "Shared Event Product",
                "list_price": 100.4,
                "type": "service",
                "service_tracking": "event",
                "company_id": False,
            }
        )
        event = self.env["event.event"].create(
            {
                "name": "Rounding Event",
                "company_id": other_company.id,
                "date_begin": "2026-10-01 09:00:00",
                "date_end": "2026-10-02 09:00:00",
            }
        )
        ticket = self.env["event.event.ticket"].create(
            {
                "name": "Rounding Ticket",
                "event_id": event.id,
                "product_id": shared_product.id,
                "price": 100.4,
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertNotEqual(
            ticket.currency_id,
            event.company_id.currency_id,
            "precondition: the product's currency is not the event company's",
        )
        self.assertEqual(
            ticket.price_incl,
            100.0,
            "price_incl must round in the event company's currency",
        )

    def test_price_reduce_taxinc_is_keyed_on_the_pricelist(self):
        """Regression for the cache key: price_reduce is pricelist-dependent, so
        reading the tax-inclusive figure under two pricelists in one transaction
        must give two answers, not whichever was computed first."""
        ticket = self.test_event.event_ticket_ids[0]
        tax = self.env["account.tax"].create(
            {
                "name": "Test Tax 25%",
                "amount": 25.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        ticket.product_id.taxes_id = [(6, 0, [tax.id])]
        ticket.product_id.list_price = 100.0
        ticket.price = 100.0
        pricelists = self.env["product.pricelist"].create(
            [
                {
                    "name": f"Discount {percent}",
                    "item_ids": [
                        (
                            0,
                            0,
                            {
                                "compute_price": "percentage",
                                "percent_price": percent,
                                "applied_on": "3_global",
                            },
                        )
                    ],
                }
                for percent in (50, 10)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()

        half, tenth = pricelists
        self.assertAlmostEqual(
            ticket.with_context(pricelist=half.id).price_reduce_taxinc, 62.5
        )
        self.assertAlmostEqual(
            ticket.with_context(pricelist=tenth.id).price_reduce_taxinc,
            112.5,
            msg="second pricelist read the first one's cached value",
        )

    def test_compute_price_keeps_a_set_price_over_a_free_product(self):
        """_compute_price is asymmetric on purpose: a product with a nonzero
        lst_price drives price, a product with a falsy one leaves it alone."""
        ticket_type = self.event_type_tickets.event_type_ticket_ids[0]
        free_product = self.env["product.product"].create(
            {
                "name": "Free Event Product",
                "list_price": 0.0,
                "type": "service",
                "service_tracking": "event",
            }
        )
        ticket_type.price = 90.0
        ticket_type.product_id = free_product.id
        self.assertEqual(ticket_type.price, 90.0, "a set price must survive")

        paid_product = self.env["product.product"].create(
            {
                "name": "Paid Event Product",
                "list_price": 70.0,
                "type": "service",
                "service_tracking": "event",
            }
        )
        ticket_type.product_id = paid_product.id
        self.assertEqual(ticket_type.price, 70.0, "a priced product must drive it")

    def test_sale_available_is_false_for_an_archived_product(self):
        """The inactive-product branch of the _compute_sale_available override."""
        ticket = self.test_event.event_ticket_ids[0]
        ticket.product_id.active = True
        self.env.invalidate_all()
        self.assertTrue(ticket.sale_available)

        ticket.product_id.active = False
        self.env.invalidate_all()
        self.assertFalse(ticket.sale_available, "an archived product cannot be sold")

    def test_ticket_fields_whitelist_copies_product_and_price(self):
        """_get_event_ticket_fields_whitelist must actually carry product_id and
        price from the event.type.ticket onto the event.event.ticket."""
        whitelist = self.env["event.type.ticket"]._get_event_ticket_fields_whitelist()
        self.assertIn("product_id", whitelist)
        self.assertIn("price", whitelist)

        ticket = self.test_event.event_ticket_ids[0]
        template = self.event_type_tickets.event_type_ticket_ids[0]
        self.assertEqual(ticket.product_id, template.product_id)

    def test_event_type_ticket_product_cannot_lose_event_tracking(self):
        """A product still referenced by a template ticket must not be able to
        leave service_tracking='event'; otherwise creating an event from that
        template fails later, far from the edit that caused it."""
        with self.assertRaises(ValidationError):
            self.event_product.service_tracking = "no"
