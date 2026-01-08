# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import users, tagged
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase


@tagged('post_install', '-at_install')
class TestImLivechatMessage(ChatbotCase):
    def setUp(self):
        super().setUp()
        self.password = 'Pl1bhD@2!kXZ'
        self.users = self.env['res.users'].create([
            {
                'email': 'e.e@example.com',
                'groups_id': [Command.link(self.env.ref('base.group_user').id)],
                'login': 'emp',
                'password': self.password,
                'name': 'Ernest Employee',
                'notification_type': 'inbox',
                'odoobot_state': 'disabled',
                'signature': '--\nErnest',
            },
            {'name': 'test1', 'login': 'test1', 'password': self.password, 'email': 'test1@example.com', 'livechat_username': 'chuck'},
        ])

    def test_update_username(self):
        user = self.env['res.users'].create({
            'name': 'User',
            'login': 'User',
            'password': self.password,
            'email': 'user@example.com',
            'livechat_username': 'edit me'
        })
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(user).check_access_rights('write')
        user.with_user(user).livechat_username = 'New username'
        self.assertEqual(user.livechat_username, 'New username')

    def test_chatbot_message_format(self):
        session = self.authenticate(self.users[0].login, self.password)
        channel_info = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Visitor",
                "channel_id": self.livechat_channel.id,
                "chatbot_script_id": self.chatbot_script.id,
                "persisted": True,
            },
            headers={
                "Cookie": f"session_id={session.sid};",
            },
        )
        mail_channel = self.env['discuss.channel'].browse(channel_info['id'])
        self._post_answer_and_trigger_next_step(
            mail_channel,
            self.step_dispatch_buy_software.name,
            chatbot_script_answer=self.step_dispatch_buy_software
        )
        chatbot_message = mail_channel.chatbot_message_ids.mail_message_id[-1:]
        self.assertEqual(
            chatbot_message.message_format(),
            [
                {
                    "attachments": [],
                    "author": {
                        "id": self.chatbot_script.operator_partner_id.id,
                        "is_company": False,
                        "name": "Testing Bot",
                        "type": "partner",
                        "user": False,
                    },
                    "body": Markup("<p>Can you give us your email please?</p>"),
                    "chatbotStep": {
                        "answers": [],
                        "id": self.step_email.id,
                        "selectedAnswerId": False,
                    },
                    "create_date": chatbot_message.create_date,
                    "date": chatbot_message.date,
                    "default_subject": "Testing Bot",
                    "history_partner_ids": [],
                    "id": chatbot_message.id,
                    "is_discussion": True,
                    "is_note": False,
                    "linkPreviews": [],
                    "message_type": "comment",
                    "model": "discuss.channel",
                    "module_icon": "/mail/static/description/icon.png",
                    "needaction_partner_ids": [],
                    "notifications": [],
                    "pinned_at": False,
                    "reactions": [],
                    "recipients": [],
                    "record_name": "Testing Bot",
                    "res_id": mail_channel.id,
                    "scheduledDatetime": False,
                    "sms_ids": [],
                    "starred_partner_ids": [],
                    "subject": False,
                    "subtype_description": False,
                    "subtype_id": (self.env.ref("mail.mt_comment").id, "Discussions"),
                    "trackingValues": [],
                    "write_date": chatbot_message.write_date,
                }
            ],
        )

    @users('emp')
    def test_message_format(self):
        im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.env['bus.presence'].create({'user_id': self.users[0].id, 'status': 'online'})  # make available for livechat (ignore leave)
        self.authenticate(self.users[1].login, self.password)
        channel_livechat_1 = self.env['discuss.channel'].browse(self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'anon 1',
            'previous_operator_id': self.users[0].partner_id.id,
            'country_id': self.env.ref('base.in').id,
            'channel_id': im_livechat_channel.id,
        })['id'])
        record_rating = self.env['rating.rating'].create({
            'res_model_id': self.env['ir.model']._get('discuss.channel').id,
            'res_id': channel_livechat_1.id,
            'parent_res_model_id': self.env['ir.model']._get('im_livechat.channel').id,
            'parent_res_id': im_livechat_channel.id,
            'rated_partner_id': self.users[0].partner_id.id,
            'partner_id': self.users[1].partner_id.id,
            'rating': 5,
            'consumed': True,
        })
        message = channel_livechat_1.message_post(
            author_id=record_rating.partner_id.id,
            body=Markup("<img src='%s' alt=':%s/5' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s")
            % (record_rating.rating_image_url, record_rating.rating, record_rating.feedback),
            rating_id=record_rating.id,
        )
        self.assertEqual(message.message_format(), [{
            'attachments': [],
            'author': {
                'id': self.users[1].partner_id.id,
                'is_company': self.users[1].partner_id.is_company,
                'user_livechat_username': self.users[1].livechat_username,
                'type': "partner",
                'user': {
                    'id': self.users[1].id,
                    'isInternalUser': self.users[1]._is_internal(),
                }
            },
            'body': message.body,
            'date': message.date,
            'write_date': message.write_date,
            'create_date': message.create_date,
            'history_partner_ids': [],
            'id': message.id,
            'default_subject': channel_livechat_1.name,
            'is_discussion': False,
            'is_note': True,
            'linkPreviews': [],
            'message_type': 'notification',
            'reactions': [],
            'model': 'discuss.channel',
            'module_icon': '/mail/static/description/icon.png',
            'needaction_partner_ids': [],
            'notifications': [],
            'pinned_at': False,
            'rating': {
                'id': record_rating.id,
                'ratingImageUrl': record_rating.rating_image_url,
                'ratingText': record_rating.rating_text,
            },
            'recipients': [],
            'record_name': "test1 Ernest Employee",
            'res_id': channel_livechat_1.id,
            'scheduledDatetime': False,
            'sms_ids': [],
            'starred_partner_ids': [],
            'subject': False,
            'subtype_description': False,
            'subtype_id': (self.env.ref('mail.mt_note').id, 'Note'),
            'trackingValues': [],
        }])
