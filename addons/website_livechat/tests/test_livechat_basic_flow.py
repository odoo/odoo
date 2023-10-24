# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import tests, _
from odoo.addons.website_livechat.tests.common import TestLivechatCommon
from odoo.tests.common import new_test_user


@tests.tagged('post_install', '-at_install')
class TestLivechatBasicFlowHttpCase(tests.HttpCase, TestLivechatCommon):
    def test_channel_created_on_user_interaction(self):
        self.start_tour('/', 'im_livechat_request_chat', login=None)
        channel = self.env['discuss.channel'].search([['livechat_active', '=', True], ['livechat_visitor_id', '=', self.visitor.id]])
        self.assertFalse(channel, 'Channel should not be created until user sends a message')
        self.start_tour('/', 'im_livechat_request_chat_and_send_message', login=None)
        channel = self.env['discuss.channel'].search([['livechat_active', '=', True], ['livechat_visitor_id', '=', self.visitor.id]])
        self.assertTrue(channel, 'Channel should be created after sending the first message')

    def test_visitor_banner_history(self):
        # create visitor history
        self.env['website.track'].create([{
            'page_id': self.env.ref('website.homepage_page').id,
            'visitor_id': self.visitor.id,
            'visit_datetime': self.base_datetime,
        }, {
            'page_id': self.env.ref('website.contactus_page').id,
            'visitor_id': self.visitor.id,
            'visit_datetime': self.base_datetime - datetime.timedelta(minutes=10),
        }, {
            'page_id': self.env.ref('website.homepage_page').id,
            'visitor_id': self.visitor.id,
            'visit_datetime': self.base_datetime - datetime.timedelta(minutes=20),
        }])

        handmade_history = "%s (21:10) → %s (21:20) → %s (21:30)" % (
            self.env.ref('website.homepage_page').name,
            self.env.ref('website.contactus_page').name,
            self.env.ref('website.homepage_page').name,
        )
        history = self.env['discuss.channel']._get_visitor_history(self.visitor)

        self.assertEqual(history, handmade_history)

    def test_livechat_username(self):
        # Open a new live chat
        res = self.opener.post(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)
        channel_1 = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_active', '=', True)], limit=1)

        # Check Channel naming
        self.assertEqual(channel_1.name, "%s %s" % (f'Visitor #{channel_1.livechat_visitor_id.id}', self.operator.livechat_username))
        channel_1.unlink()

        # Remove livechat_username
        self.operator.livechat_username = False

        # This fixes an issue in the controller, possibly related to the testing
        # environment.  The business code unexpectedly uses two cache objects
        # (env.cache), which triggers cache misses: a field is computed with its
        # value stored into one cache and retrieved from another cache :-/
        self.operator.name

        # Open a new live chat
        res = self.opener.post(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)
        channel_2 = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_active', '=', True)], limit=1)

        # Check Channel naming
        self.assertEqual(channel_2.name, "%s %s" % (f'Visitor #{channel_2.livechat_visitor_id.id}', self.operator.name))

    def test_basic_flow_with_rating(self):
        channel = self._common_basic_flow()

        self._send_rating(channel, self.visitor, 5, "This deboulonnage was fine but not topitop.")

        channel._close_livechat_session()

        self.assertEqual(len(channel.message_ids), 4)
        self.assertEqual(channel.message_ids[0].author_id, self.env.ref('base.partner_root'), "Odoobot must be the sender of the 'left the conversation' message.")
        self.assertIn(f"Visitor #{channel.livechat_visitor_id.id}", channel.message_ids[0].body)
        self.assertEqual(channel.livechat_active, False, "The livechat session must be inactive as the visitor sent his feedback.")

    def test_basic_flow_without_rating(self):
        channel = self._common_basic_flow()

        # left the conversation
        channel._close_livechat_session()
        self.assertEqual(len(channel.message_ids), 3)
        self.assertEqual(channel.message_ids[0].author_id, self.env.ref('base.partner_root'), "Odoobot must be the author the message.")
        self.assertIn(f"Visitor #{channel.livechat_visitor_id.id}", channel.message_ids[0].body)
        self.assertEqual(channel.livechat_active, False, "The livechat session must be inactive since visitor left the conversation.")

    def test_visitor_info_access_rights(self):
        channel = self._common_basic_flow()
        self.authenticate(self.operator.login, 'ideboulonate')

        # Retrieve channels information, visitor info should be there
        res = self.opener.post(self.message_info_url, json={})
        self.assertEqual(res.status_code, 200)
        messages_info = res.json().get('result', {})
        livechat_info = next(c for c in messages_info['channels'] if c['id'] == channel.id)
        self.assertIn('visitor', livechat_info)

        # Remove access to visitors and try again, visitors info shouldn't be included
        self.operator.groups_id -= self.group_livechat_user
        res = self.opener.post(self.message_info_url, json={})
        self.assertEqual(res.status_code, 200)
        messages_info = res.json().get('result', {})
        livechat_info = next(c for c in messages_info['channels'] if c['id'] == channel.id)
        self.assertNotIn('visitor', livechat_info)

    def _common_basic_flow(self):
        # Open a new live chat
        res = self.opener.post(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)

        channel = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_active', '=', True)], limit=1)

        # Check Channel and Visitor naming
        self.assertEqual(self.visitor.display_name, "%s #%s" % (_("Website Visitor"), self.visitor.id))
        self.assertEqual(channel.name, "%s %s" % (f'Visitor #{channel.livechat_visitor_id.id}', self.operator.livechat_username))

        # Post Message from visitor
        self._send_message(channel, self.visitor.display_name, "Message from Visitor")

        self.assertEqual(len(channel.message_ids), 1)
        self.assertEqual(channel.message_ids[0].author_id.id, False, "The author of the message is not a partner.")
        self.assertEqual(channel.message_ids[0].email_from, self.visitor.display_name, "The sender's email should be the visitor's email.")
        self.assertEqual(channel.message_ids[0].body, "<p>Message from Visitor</p>")
        self.assertEqual(channel.livechat_active, True, "The livechat session must be active as the visitor did not left the conversation yet.")

        # Post message from operator
        self._send_message(channel, self.operator.email, "Message from Operator", author_id=self.operator.partner_id.id)

        self.assertEqual(len(channel.message_ids), 2)
        self.assertEqual(channel.message_ids[0].author_id, self.operator.partner_id, "The author of the message should be the operator.")
        self.assertEqual(channel.message_ids[0].email_from, self.operator.email, "The sender's email should be the operator's email.")
        self.assertEqual(channel.message_ids[0].body, "<p>Message from Operator</p>")
        self.assertEqual(channel.livechat_active, True, "The livechat session must be active as the visitor did not left the conversation yet.")

        return channel

    def test_livechat_as_portal_user(self):
        new_test_user(self.env, login="portal_user", groups="base.group_portal")
        self.start_tour("/my", "website_livechat_as_portal_tour", login="portal_user")
