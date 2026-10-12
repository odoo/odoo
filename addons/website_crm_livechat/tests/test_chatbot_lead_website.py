# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm_livechat.tests import test_chatbot_lead
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class WebsiteCrmChatbotCase(MockVisitor, test_chatbot_lead.CrmChatbotCase):

    def test_chatbot_lead_website_public_user(self):
        """" Additionally test that we use the visitor data. """
        website_visitor = self.env['website.visitor'].sudo().create({
            "access_token": "c8d20bd006c3bf46b875451defb5991d"
        })
        partner = self.env['res.partner'].sudo().create({"name": "Jean Michel Visitor"})
        website_visitor.partner_id = partner.id  # can't be set in create as compute overrides it
        with self.mock_visitor_from_request(force_visitor=website_visitor):
            self._play_session_with_lead()
        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')

        self.assertEqual(created_lead.name, "Jean Michel Visitor's New Lead")
        self.assertEqual(created_lead.visitor_ids, website_visitor)
        self.assertEqual(created_lead.medium_id, self.env.ref("utm.utm_medium_website"))
