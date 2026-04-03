# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged

from odoo.addons.website_event_exhibitor.tests.common import TestEventExhibitorCommon


@tagged("post_install", "-at_install")
class TestWebsiteEventExhibitorJsonLd(TestEventExhibitorCommon):
    def test_sponsor_to_structured_data_summary(self):
        website = self.env.ref("website.default_website")

        json_ld = self.sponsor_0._to_structured_data_summary(website)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Organization")
        self.assertEqual(markup_data["name"], self.sponsor_0.name)

    def test_sponsor_to_structured_data(self):
        website = self.env.ref("website.default_website")
        self.sponsor_0.subtitle = "Short exhibitor subtitle"
        self.sponsor_0.website_description = "Detailed exhibitor description"

        json_ld = self.sponsor_0._to_structured_data(website)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Organization")
        self.assertIn("description", markup_data)

    def test_sponsor_summary_and_detail_description_difference(self):
        website = self.env.ref("website.default_website")
        self.sponsor_0.subtitle = "Summary description"
        self.sponsor_0.website_description = "Detail page long description"

        summary_markup = self.sponsor_0._to_structured_data_summary(website)._render()
        detail_markup = self.sponsor_0._to_structured_data(website)._render()

        self.assertEqual(summary_markup["description"], "Summary description")
        self.assertEqual(detail_markup["description"], "Detail page long description")
