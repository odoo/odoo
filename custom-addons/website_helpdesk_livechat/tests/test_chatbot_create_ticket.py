# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_helpdesk_livechat.tests.helpdesk_livechat_chatbot_common import HelpdeskChatbotCase
from odoo.tests.common import users


class TestChatbotCreateTicket(HelpdeskChatbotCase):

    @users('user_public')
    def test_chatbot_helpdesk_ticket_public_user(self):
        """ Create a ticket from a public user and check that information are correctly propagated. """
        self._chatbot_create_helpdesk_ticket(self.user_public)

        created_ticket = self.env['helpdesk.ticket'].sudo().search([
            ('name', '=', "Testing Bot's Ticket")
        ], limit=1)
        self.assertEqual(created_ticket.partner_email, 'helpme@example.com')
        self.assertEqual(created_ticket.partner_phone, '+32499112233')

        self.assertIn('There is a problem with my printer.', created_ticket.description)
        self.assertIn('helpme@example.com', created_ticket.description)
        self.assertIn('+32499112233', created_ticket.description)

        self.assertFalse(bool(created_ticket.team_id))

    @users('user_portal')
    def test_chatbot_helpdesk_ticket_portal_user(self):
        """ Create a ticket from a portal user and check that information are correctly propagated. """
        self.step_helpdesk_create_ticket.write({'helpdesk_team_id': self.helpdesk_team.id})
        self._chatbot_create_helpdesk_ticket(self.user_portal)

        created_ticket = self.env['helpdesk.ticket'].sudo().search([
            ('name', '=', "Testing Bot's Ticket")
        ], limit=1)
        # should use email defined on base partner since it's not empty
        self.assertNotEqual(created_ticket.partner_email, 'helpme@example.com', "")
        # phone however WAS empty -> check that it has been updated
        self.assertEqual(created_ticket.partner_phone, '+32499112233')

        self.assertEqual(created_ticket.team_id, self.helpdesk_team)

    def _chatbot_create_helpdesk_ticket(self, user):
        channel_info = self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'Test Visitor',
            'channel_id': self.livechat_channel.id,
            'chatbot_script_id': self.chatbot_script.id,
            'user_id': user.id,
        })
        discuss_channel = self.env['discuss.channel'].sudo().browse(channel_info['id'])

        self._post_answer_and_trigger_next_step(
            discuss_channel,
            self.step_selection_ticket.name,
            chatbot_script_answer=self.step_selection_ticket
        )

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_helpdesk_issue)
        self._post_answer_and_trigger_next_step(discuss_channel, 'There is a problem with my printer.')

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_helpdesk_email)
        self._post_answer_and_trigger_next_step(discuss_channel, 'helpme@example.com')

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_helpdesk_phone)
        self._post_answer_and_trigger_next_step(discuss_channel, '+32499112233')

        self.assertEqual(discuss_channel.chatbot_current_step_id, self.step_helpdesk_create_ticket)
