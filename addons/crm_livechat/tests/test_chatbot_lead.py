# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch, PropertyMock

from odoo import Command
from odoo.addons.crm_livechat.tests import chatbot_common
from odoo.fields import Domain


class CrmChatbotCase(chatbot_common.CrmChatbotCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.belgium = cls.env.ref('base.be')
        cls.belgium_fr_lang = cls.env["res.lang"].search(
            Domain("code", "=", "fr_BE") & Domain("active", "=", False), limit=1
        )
        cls.belgium_fr_lang.active = True

    def test_chatbot_create_lead_public_user(self):
        self._play_session_with_lead()

        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')
        self.assertEqual(created_lead.name, "Nouvelle piste de Testing Bot")
        self.assertEqual(created_lead.email_from, 'test2@example.com')
        self.assertEqual(created_lead.phone, "+919876543210")
        self.assertEqual(created_lead.lang_id, self.belgium_fr_lang)
        self.assertEqual(created_lead.country_id, self.belgium)
        self.assertEqual(created_lead.team_id, self.sale_team)
        self.assertEqual(created_lead.type, 'opportunity')

    def test_chatbot_create_lead_portal_user(self):
        self.authenticate(self.user_portal.login, self.user_portal.login)
        self.step_create_lead.write({'crm_team_id': self.sale_team_with_lead})
        self._play_session_with_lead(self.user_portal)

        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')
        self.assertEqual(created_lead.name, "Testing Bot's New Lead")
        self.assertNotEqual(created_lead.email_from, 'test2@example.com', "User's email should'nt have been overridden")
        self.assertEqual(created_lead.phone, "+919876543210", "User's phone should have been updated")

        self.assertEqual(created_lead.team_id, self.sale_team_with_lead)
        self.assertEqual(created_lead.type, 'lead')
        self.assertEqual(created_lead.country_id, self.belgium)
        self.assertEqual(created_lead.lang_id.code, self.user_portal.lang)

    def test_chatbot_create_lead_company(self):
        self.user_portal.write({"company_ids": self.company_2, "company_id": self.company_2})
        team = self.sale_team_with_lead
        partner = self.user_portal.partner_id
        self.step_create_lead.crm_team_id = team
        self.authenticate(self.user_portal.login, self.user_portal.login)

        def play_script_and_get_created_lead():
            self.env["crm.lead"].search([]).unlink()
            self._play_session_with_lead()
            return self.env["crm.lead"].sudo().search([], limit=1, order="id desc")

        # lead has company of partner and no team if no company matching
        partner.company_id = self.company_2
        team.company_id = self.company_3
        lead = play_script_and_get_created_lead()
        self.assertEqual(lead.company_id, self.company_2)
        self.assertFalse(lead.team_id)
        # lead has common company of partner and team if both are matching
        partner.company_id = self.company_2
        team.company_id = self.company_2
        self.assertEqual(play_script_and_get_created_lead().company_id, self.company_2)
        # lead has team company if partner has no company
        partner.company_id = False
        team.company_id = self.company_2
        self.assertEqual(play_script_and_get_created_lead().company_id, self.company_2)
        # lead has partner company if team has no company
        partner.company_id = self.company_2
        team.company_id = False
        self.assertEqual(play_script_and_get_created_lead().company_id, self.company_2)
        # lead has no company if no company on partner and team
        partner.company_id = False
        team.company_id = False
        self.assertFalse(play_script_and_get_created_lead().company_id)

    def _play_session_with_lead(self, user=None):
        with patch(
            "odoo.http.geoip.GeoIP.country_code",
            new_callable=PropertyMock(return_value=self.belgium.code),
        ):
            data = self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "channel_id": self.livechat_channel.id,
                    "chatbot_script_id": self.chatbot_script.id,
                },
                cookies={
                    "frontend_lang": self.belgium_fr_lang.code if not user else user.lang,
                },
            )
            discuss_channel = (
                self.env["discuss.channel"].sudo().browse(data["channel_id"])
            )
            self._post_answer_and_trigger_next_step(
                discuss_channel, chatbot_script_answer=self.step_dispatch_create_lead
            )
            self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead_email)
            self._post_answer_and_trigger_next_step(discuss_channel, email="test2@example.com")
            self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead_phone)
            self._post_answer_and_trigger_next_step(
                discuss_channel,
                "+919876543210",
                trigger_cookies={
                    "frontend_lang": self.belgium_fr_lang.code if not user else user.lang
                },
            )
            self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead)
            return discuss_channel

    def test_create_lead_from_chatbot(self):
        chatbot_script = self.env["chatbot.script"].create({"title": "Create lead bot"})
        self.env["chatbot.script.step"].create(
            [
                {
                    "chatbot_script_id": chatbot_script.id,
                    "message": "Hello, how can I help you?",
                    "step_type": "free_input_single",
                },
                {
                    "step_type": "question_email",
                    "chatbot_script_id": chatbot_script.id,
                    "message": "Would you mind leaving your email address so that we can reach you back?",
                },
                {
                    "step_type": "create_lead",
                    "chatbot_script_id": chatbot_script.id,
                    "message": "Thank you, you should hear back from us very soon!",
                },
            ]
        )
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Create lead channel",
                "rule_ids": [
                    Command.create(
                        {
                            "regex_url": "/",
                            "chatbot_script_id": chatbot_script.id,
                        }
                    )
                ],
            }
        )
        self.start_tour(
            f"/im_livechat/support/{livechat_channel.id}", "crm_livechat.create_lead_from_chatbot"
        )
        lead = self.env["crm.lead"].search([("origin_channel_id", "=", livechat_channel.channel_ids.id)])
        self.assertEqual(lead.name, "I'd like to know more about the CRM application.")
        self.assertTrue(lead.origin_channel_id.has_crm_lead)
