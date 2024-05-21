# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm_livechat.tests import chatbot_common
from odoo.tests.common import tagged, users


@tagged("post_install", "-at_install")
class CrmChatbotCase(chatbot_common.CrmChatbotCase):

    @users('user_public')
    def test_chatbot_lead_public_user(self):
        self._chatbot_create_lead(self.user_public)

        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')
        self.assertEqual(created_lead.name, "Testing Bot's New Lead")
        self.assertEqual(created_lead.email_from, 'test2@example.com')
        self.assertEqual(created_lead.phone, '123456')

        self.assertEqual(created_lead.team_id, self.sale_team)
        self.assertEqual(created_lead.type, 'opportunity')

    @users('user_portal')
    def test_chatbot_lead_portal_user(self):
        self.step_create_lead.write({'crm_team_id': self.sale_team_with_lead})
        self._chatbot_create_lead(self.user_portal)

        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')
        self.assertEqual(created_lead.name, "Testing Bot's New Lead")
        self.assertNotEqual(created_lead.email_from, 'test2@example.com', "User's email should'nt have been overridden")
        self.assertEqual(created_lead.phone, '123456', "User's phone should have been updated")

        self.assertEqual(created_lead.team_id, self.sale_team_with_lead)
        self.assertEqual(created_lead.type, 'lead')

    def _chatbot_create_lead(self, user):
        channel_info = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Test Visitor',
            'channel_id': self.livechat_channel.id,
            'chatbot_script_id': self.chatbot_script.id,
            'user_id': user.id,
        })["Thread"]
        discuss_channel = self.env['discuss.channel'].browse(channel_info['id'])  # <- sudo removed
        # discuss_channel.add_members(guest_ids= guest.ids, post_joined_message=post_joined_message)


        # discuss_channel._find_or_create_member_for_self()
        # __, guest = channel.sudo()._find_or_create_persona_for_channel(
        #             guest_name=self._get_guest_name(),
        #             country_code=request.geoip.country_code,
        #             timezone=request.env['mail.guest']._get_timezone_from_request(request),
        #             post_joined_message=False
        #         )
        # self.env.invalidate_all()
        self._post_answer_and_trigger_next_step(
            discuss_channel,
            self.step_dispatch_create_lead.name,
            chatbot_script_answer=self.step_dispatch_create_lead
        )
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead_email)
        self._post_answer_and_trigger_next_step(discuss_channel, 'test2@example.com')

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead_phone)
        self._post_answer_and_trigger_next_step(discuss_channel, '123456')

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead)
