# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import TransactionCase, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_partner.controllers.main import WebsitePartnerPage


@tagged("post_install", "-at_install")
class TestWebsitePartnerJsonLd(TransactionCase):
    def test_partner_to_structured_data(self):
        website = self.env.ref("website.default_website")
        partner = self.env["res.partner"].create({
            "name": "JSON-LD Partner",
            "website_short_description": "Partner visible description.",
        })

        json_ld = partner._to_structured_data(website)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Organization")
        self.assertEqual(markup_data["name"], partner.name)
        self.assertEqual(markup_data["description"], partner.website_short_description)

    def test_partner_detail_values_include_composed_structured_data(self):
        website = self.env.ref("website.default_website")
        partner = self.env["res.partner"].create({
            "name": "JSON-LD Detail Partner",
            "is_published": True,
        })

        with MockRequest(self.env, website=website):
            values = WebsitePartnerPage()._get_partners_detail_values(partner.id)

        payload = json.loads(values["partner_structured_data"])

        self.assertEqual(len(payload), 3)
        self.assertEqual(payload[1]["@type"], "Organization")
        self.assertEqual(payload[2]["@type"], "BreadcrumbList")
