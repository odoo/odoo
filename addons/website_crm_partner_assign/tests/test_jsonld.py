# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_crm_partner_assign.controllers.main import WebsiteCrmPartnerAssign


@tagged("post_install", "-at_install")
class TestWebsiteCrmPartnerAssignJsonLd(TransactionCase):
    def test_partners_breadcrumb_structured_data(self):
        website = self.env.ref("website.default_website")

        with MockRequest(self.env, website=website):
            breadcrumb = WebsiteCrmPartnerAssign()._get_partners_breadcrumb_structured_data()

        markup_data = breadcrumb._render()

        self.assertEqual(markup_data["@type"], "BreadcrumbList")
        self.assertEqual(len(markup_data["itemListElement"]), 2)
        self.assertEqual(markup_data["itemListElement"][1]["name"], "Partners")
