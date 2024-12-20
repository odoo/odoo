# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.crm_livechat.tests import chatbot_common
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class CrmChatbotCase(chatbot_common.CrmChatbotCase):

    def test_chatbot_create_lead_public_user(self):
        self._play_session_with_lead()

        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')
        self.assertEqual(created_lead.name, "Testing Bot's New Lead")
        self.assertEqual(created_lead.email_from, 'test2@example.com')
        self.assertEqual(created_lead.phone, '123456')

        self.assertEqual(created_lead.team_id, self.sale_team)
        self.assertEqual(created_lead.type, 'opportunity')

    def test_chatbot_create_lead_and_forward_public_user(self):
        """Test create_lead_and_forward properly creates a lead, assigns it to an available sales
        team member, and forwards the discussion to that member."""
        self.step_create_lead.sudo().step_type = "create_lead_and_forward"
        discuss_channel = self._play_session_with_lead()
        not_available_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertEqual(not_available_lead.name, "Testing Bot's New Lead")
        self.assertEqual(not_available_lead.email_from, "test2@example.com")
        self.assertEqual(not_available_lead.phone, "123456")
        self.assertEqual(not_available_lead.team_id, self.sale_team)
        self.assertEqual(not_available_lead.type, "opportunity")
        chatbot_partner = self.chatbot_script.operator_partner_id
        # sales team member is not available
        self.assertFalse(not_available_lead.user_id)
        self.assertEqual(discuss_channel.livechat_operator_id, chatbot_partner)
        # sales team member is available
        self.env["bus.presence"].create({"user_id": self.user_employee.id, "status": "online"})
        discuss_channel = self._play_session_with_lead()
        assigned_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertEqual(assigned_lead.user_id, self.user_employee)
        self.assertEqual(discuss_channel.livechat_operator_id, self.partner_employee)
        # sales team member quota is reached (lead already assigned before)
        discuss_channel = self._play_session_with_lead()
        quota_reached_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertFalse(quota_reached_lead.user_id)
        self.assertEqual(discuss_channel.livechat_operator_id, chatbot_partner)
        assigned_lead.unlink()
        # sales team member opt out
        self.sale_team.crm_team_member_ids.assignment_optout = True
        discuss_channel = self._play_session_with_lead()
        optout_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertFalse(optout_lead.user_id)
        self.assertEqual(discuss_channel.livechat_operator_id, chatbot_partner)
        self.sale_team.crm_team_member_ids.assignment_optout = False
        # sales team member invalid domain (probability of lead is 5.39)
        self.sale_team.crm_team_member_ids.assignment_domain = "[('probability', '>=', 20)]"
        discuss_channel = self._play_session_with_lead()
        non_matching_domain_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertFalse(non_matching_domain_lead.user_id)
        self.assertEqual(discuss_channel.livechat_operator_id, chatbot_partner)
        self.sale_team.crm_team_member_ids.assignment_domain = False
        # auto-assign team
        self.step_create_lead.crm_team_id = False
        discuss_channel = self._play_session_with_lead()
        auto_team_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertEqual(auto_team_lead.user_id, self.user_employee)
        self.assertEqual(auto_team_lead.team_id, self.sale_team)
        self.assertEqual(discuss_channel.livechat_operator_id, self.partner_employee)
        auto_team_lead.unlink()
        # sales team opt out
        self.sale_team.assignment_optout = True
        discuss_channel = self._play_session_with_lead()
        team_optout_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertFalse(team_optout_lead.user_id)
        self.assertEqual(discuss_channel.livechat_operator_id, chatbot_partner)
        self.sale_team.assignment_optout = False
        # sales team invalid domain (probability of lead is 5.39)
        self.sale_team.assignment_domain = "[('probability', '>=', 20)]"
        discuss_channel = self._play_session_with_lead()
        team_non_matching_domain_lead = self.env["crm.lead"].sudo().search([], limit=1, order="id desc")
        self.assertFalse(team_non_matching_domain_lead.user_id)
        self.assertEqual(discuss_channel.livechat_operator_id, chatbot_partner)

    def test_chatbot_create_lead_portal_user(self):
        self.authenticate(self.user_portal.login, self.user_portal.login)
        self.step_create_lead.write({'crm_team_id': self.sale_team_with_lead})
        self._play_session_with_lead()

        created_lead = self.env['crm.lead'].sudo().search([], limit=1, order='id desc')
        self.assertEqual(created_lead.name, "Testing Bot's New Lead")
        self.assertNotEqual(created_lead.email_from, 'test2@example.com', "User's email should'nt have been overridden")
        self.assertEqual(created_lead.phone, '123456', "User's phone should have been updated")

        self.assertEqual(created_lead.team_id, self.sale_team_with_lead)
        self.assertEqual(created_lead.type, 'lead')

    def _play_session_with_lead(self):
        data = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Test Visitor',
            'channel_id': self.livechat_channel.id,
            'chatbot_script_id': self.chatbot_script.id,
        })
        discuss_channel = (
            self.env["discuss.channel"].sudo().browse(data["discuss.channel"][0]["id"])
        )
        self._post_answer_and_trigger_next_step(
            discuss_channel, chatbot_script_answer=self.step_dispatch_create_lead
        )
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead_email)
        self._post_answer_and_trigger_next_step(discuss_channel, email="test2@example.com")
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead_phone)
        self._post_answer_and_trigger_next_step(discuss_channel, '123456')
        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_create_lead)
        return discuss_channel
