# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_slides.tests.common import SlidesCase


@tagged("post_install", "-at_install")
class TestWebsiteSlidesJsonLd(SlidesCase):
    def test_channel_to_structured_data(self):
        website = self.env.ref("website.default_website")

        json_ld = self.channel._to_structured_data(website)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "Course")
        self.assertEqual(markup_data["name"], self.channel.name)
        self.assertEqual(markup_data["provider"]["@type"], "Organization")

    def test_channel_to_structured_data_with_just_id(self):
        website = self.env.ref("website.default_website")

        json_ld = self.channel._to_structured_data(website, just_id=True)
        markup_data = json_ld._render()

        self.assertEqual(markup_data["provider"]["@id"], f"{website.get_base_url()}/#organization")
