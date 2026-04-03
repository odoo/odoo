# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.website_event.tests.common import OnlineEventCase


@tagged("post_install", "-at_install")
class TestWebsiteEventJsonLd(OnlineEventCase):
    def test_event_structured_data_summary(self):
        website = self.env.ref("website.default_website")
        event = self.env["event.event"].create({
            "name": "Website Event JSON-LD",
            "date_begin": fields.Datetime.now() + timedelta(days=10),
            "date_end": fields.Datetime.now() + timedelta(days=11),
            "website_published": True,
            "address_id": self.env.user.partner_id.id,
            "address_name": self.env.user.partner_id.name,
        })

        json_ld = event._to_structured_data_summary(website)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Event")
        self.assertEqual(markup_data["name"], event.name)
        self.assertEqual(markup_data["location"]["@type"], "Place")

    def test_event_structured_data_has_no_schema_for_ongoing_event(self):
        website = self.env.ref("website.default_website")
        event = self.env["event.event"].create({
            "name": "Ongoing Event",
            "date_begin": fields.Datetime.now() - timedelta(days=1),
            "date_end": fields.Datetime.now() + timedelta(days=1),
            "website_published": True,
            "address_id": self.env.user.partner_id.id,
            "address_name": self.env.user.partner_id.name,
        })

        self.assertFalse(event._to_structured_data_summary(website))
        self.assertFalse(event._to_structured_data(website))

    def test_event_structured_data_has_no_schema_for_past_event(self):
        website = self.env.ref("website.default_website")
        event = self.env["event.event"].create({
            "name": "Past Event",
            "date_begin": fields.Datetime.now() - timedelta(days=10),
            "date_end": fields.Datetime.now() - timedelta(days=9),
            "website_published": True,
            "address_id": self.env.user.partner_id.id,
            "address_name": self.env.user.partner_id.name,
        })

        self.assertFalse(event._to_structured_data_summary(website))
        self.assertFalse(event._to_structured_data(website))

    def test_event_structured_data_has_no_schema_for_private_event(self):
        website = self.env.ref("website.default_website")
        event = self.env["event.event"].create({
            "name": "Private Event",
            "date_begin": fields.Datetime.now() + timedelta(days=5),
            "date_end": fields.Datetime.now() + timedelta(days=6),
            "website_published": True,
            "website_visibility": "logged_users",
            "address_id": self.env.user.partner_id.id,
            "address_name": self.env.user.partner_id.name,
        })

        self.assertFalse(event._to_structured_data_summary(website))
        self.assertFalse(event._to_structured_data(website))

    def test_event_structured_data_includes_offers(self):
        website = self.env.ref("website.default_website")
        event = self.env["event.event"].create({
            "name": "Website Event With Ticket JSON-LD",
            "date_begin": fields.Datetime.now() + timedelta(days=15),
            "date_end": fields.Datetime.now() + timedelta(days=16),
            "website_published": True,
            "address_id": self.env.user.partner_id.id,
            "address_name": self.env.user.partner_id.name,
            "event_ticket_ids": [
                (0, 0, {
                    "name": "General",
                }),
            ],
        })

        json_ld = event._to_structured_data(website)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Event")
        self.assertEqual(markup_data["offers"]["@type"], "Offer")
        self.assertEqual(markup_data["offers"]["availability"], "https://schema.org/InStock")

    def test_event_online_has_no_schema(self):
        website = self.env.ref("website.default_website")
        event = self.env["event.event"].create({
            "name": "Online Event Without Physical Place",
            "date_begin": fields.Datetime.now() + timedelta(days=8),
            "date_end": fields.Datetime.now() + timedelta(days=9),
            "website_published": True,
            "address_id": False,
        })

        self.assertFalse(event._to_structured_data_summary(website))
        self.assertFalse(event._to_structured_data(website))

    def test_event_listing_only_keeps_valid_schemas(self):
        website = self.env.ref("website.default_website")
        physical_event = self.env["event.event"].create({
            "name": "Physical Event",
            "date_begin": fields.Datetime.now() + timedelta(days=12),
            "date_end": fields.Datetime.now() + timedelta(days=13),
            "website_published": True,
            "address_id": self.env.user.partner_id.id,
            "address_name": self.env.user.partner_id.name,
        })
        online_event = self.env["event.event"].create({
            "name": "Online Event",
            "date_begin": fields.Datetime.now() + timedelta(days=12),
            "date_end": fields.Datetime.now() + timedelta(days=13),
            "website_published": True,
            "address_id": False,
        })

        schemas = [
            schema for schema in [
                physical_event._to_structured_data_summary(website),
                online_event._to_structured_data_summary(website),
            ]
            if schema
        ]

        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]._render()["name"], "Physical Event")
