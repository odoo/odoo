# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, tests
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


@tests.tagged('post_install', '-at_install')
class TestWebsiteCrmLivechatUI(TestLivechatCommon, ChatbotCase):
    def setUp(self):
        super().setUp()
        self.env['im_livechat.channel'].search([
            ('id', '!=', self.livechat_channel.id)
        ]).unlink()  # delete other channels to avoid them messing with the URL rules

        self.livechat_channel.write({
            'is_published': True,
            'rule_ids': [(5, 0), (0, 0, {
                'action': 'auto_popup',
                'regex_url': '/',
                'chatbot_script_id': self.chatbot_script.id,
            })]
        })

        self.env.ref('website.default_website').channel_id = self.livechat_channel.id

    def test_create_lead_as_public(self):
        chatbot_creating_leads_script = self.env["chatbot.script"].create(
            {"title": "Lead Creation Bot Script"}
        )
        self.env["chatbot.script.step"].create([
            {
                "chatbot_script_id": chatbot_creating_leads_script.id,
                "message": "Phone number please",
                "step_type": "question_phone",
            }, {
                "chatbot_script_id": chatbot_creating_leads_script.id,
                "message": "Email please",
                "step_type": "question_email",
            }, {
                "chatbot_script_id": chatbot_creating_leads_script.id,
                "message": "Creating lead",
                "step_type": "create_lead",
            }, {
                "chatbot_script_id": chatbot_creating_leads_script.id,
                "message": "Message to wait for in a tour",
                "step_type": "text",
            }
        ])
        livechat_channel = self.env["im_livechat.channel"].create({
            'name': 'Lead Creation Bot',
            'rule_ids': [Command.create({
                'regex_url': '/contactus',
                'chatbot_script_id': chatbot_creating_leads_script.id,
            })]
        })
        default_website = self.env.ref("website.default_website")
        default_website.channel_id = livechat_channel.id
        self.env.ref("website.default_website").channel_id = livechat_channel.id
        self.start_tour("/contactus", "website_crm_livechat.create_lead_as_public")

        # Confirm that lead was created (uses email used in tour)
        self.assertTrue(self.env['crm.lead'].search([('email_from', 'ilike', 'bot_should_create_lead_with_this_email@test.com')]),
            "Lead wasn't created (Check if pulbic user has access to livechat_visitor_id)")
