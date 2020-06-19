# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


@tests.tagged('post_install', '-at_install')
class TestLivechatRequestHttpCase(tests.HttpCase, TestLivechatCommon):
    def test_livechat_request_complete_flow(self):
        self._clean_livechat_sessions()

        # Send first chat request - Open chat from operator side
        channel_1 = self._common_chat_request_flow()
        # Visitor Rates the conversation (Good)
        self._send_rating(channel_1, self.visitor, 5)

        # Operator Re-Send a chat request
        channel_2 = self._common_chat_request_flow()
        # Visitor Rates the conversation (Bad)
        self._send_rating(channel_2, self.visitor, 1, "Stop bothering me! I hate you </3 !")

    def test_cancel_chat_request_on_visitor_demand(self):
        self._clean_livechat_sessions()

        self.operator_b = self.env['res.users'].create({
            'name': 'Operator Marc',
            'login': 'operator_b',
            'email': 'operatormarc@example.com',
            'password': "operatormarc",
            'livechat_username': "Marco'r El",
        })

        # Open Chat Request
        self.visitor.with_user(self.operator_b).action_send_chat_request()
        chat_request = self.env['mail.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_active', '=', True)])
        self.assertEqual(chat_request.livechat_operator_id, self.operator_b.partner_id, "Operator for active livechat session must be Operator Marc")

        # Click on livechatbutton at client side
        res = self.opener.post(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)
        channel = self.env['mail.channel'].search([('livechat_visitor_id', '=', self.visitor.id),
                                                   ('livechat_active', '=', True)])

        # Check that the chat request has been canceled.
        chat_request.invalidate_cache()
        self.assertEqual(chat_request.livechat_active, False, "The livechat request must be inactive as the visitor started himself a livechat session.")
        self.assertEqual(len(channel), 1)
        self.assertEqual(channel.livechat_operator_id, self.operator.partner_id, "Operator for active livechat session must be Michel Operator")

    def _common_chat_request_flow(self):
        self.visitor.with_user(self.operator).action_send_chat_request()
        channel = self.env['mail.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_active', '=', True)])
        self.assertEqual(len(channel), 1)
        self.assertEqual(channel.livechat_operator_id, self.operator.partner_id, "Michel Operator should be the operator of this channel.")
        self.assertEqual(len(channel.message_ids), 0)

        # Operator Sends message
        self._send_message(channel, self.operator.email, "Hello Again !", author_id=self.operator.partner_id.id)
        self.assertEqual(len(channel.message_ids), 1)

        # Visitor Answers
        self._send_message(channel, self.visitor.display_name, "Answer from Visitor")
        self.assertEqual(len(channel.message_ids), 2)

        # Visitor Leave the conversation
        channel._close_livechat_session()
        self.assertEqual(len(channel.message_ids), 3)
        self.assertEqual(channel.message_ids[0].author_id, self.env.ref('base.partner_root'), "Odoobot must be the sender of the 'has left the conversation' message.")
        self.assertEqual(channel.message_ids[0].body, "<p>%s has left the conversation.</p>" % self.visitor.display_name)
        self.assertEqual(channel.livechat_active, False, "The livechat session must be inactive as the visitor sent his feedback.")

        return channel

    def _clean_livechat_sessions(self):
        # clean every possible mail channel linked to the visitor
        active_channels = self.env['mail.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_active', '=', True)])
        for active_channel in active_channels:
            active_channel._close_livechat_session()
