# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import users, tagged
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase


@tagged('post_install', '-at_install')
class TestImLivechatMessage(ChatbotCase):
    def setUp(self):
        super().setUp()
        self.users = self.env['res.users'].create([
            {
                'email': 'e.e@example.com',
                'groups_id': [Command.link(self.env.ref('base.group_user').id)],
                'login': 'emp',
                'name': 'Ernest Employee',
                'notification_type': 'inbox',
                'odoobot_state': 'disabled',
                'signature': '--\nErnest',
            },
            {'name': 'test1', 'login': 'test1', 'email': 'test1@example.com'},
        ])

    @users('emp')
    def test_chatbot_message_format(self):
        user = self.env.user
        channel_info = self.livechat_channel.with_user(user)._open_livechat_mail_channel(
            anonymous_name='Test Chatbot',
            previous_operator_id=self.chatbot_script.operator_partner_id.id,
            chatbot_script=self.chatbot_script,
            user_id=user.id
        )
        mail_channel = self.env['mail.channel'].browse(channel_info['id'])
        self._post_answer_and_trigger_next_step(
            mail_channel,
            self.step_dispatch_buy_software.name,
            chatbot_script_answer=self.step_dispatch_buy_software
        )
        chatbot_message = mail_channel.chatbot_message_ids.mail_message_id[-1:]
        self.assertEqual(chatbot_message.message_format(), [{
            'id': chatbot_message.id,
            'body': '<p>Can you give us your email please?</p>',
            'date': chatbot_message.date,
            'message_type': 'comment',
            'subtype_id': (self.env.ref('mail.mt_comment').id, 'Discussions'),
            'subject': False,
            'model': 'mail.channel',
            'res_id': mail_channel.id,
            'record_name': 'Testing Bot',
            'starred_partner_ids': [],
            'author': {
                'id': self.chatbot_script.operator_partner_id.id,
                'name': 'Testing Bot'
            },
            'guestAuthor': [('clear',)],
            'notifications': [],
            'attachment_ids': [],
            'trackingValues': [],
            'linkPreviews': [],
            'messageReactionGroups': [],
            'chatbot_script_step_id': self.step_email.id,
            'needaction_partner_ids': [],
            'history_partner_ids': [],
            'is_note': False,
            'is_discussion': True,
            'subtype_description': False,
            'is_notification': False,
            'recipients': [],
            'module_icon': '/mail/static/description/icon.png',
            'sms_ids': []
        }])

    @users('emp')
    def test_message_format(self):
        im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.users[0].im_status = 'online'  # make available for livechat (ignore leave)
        channel_livechat_1 = self.env['mail.channel'].browse(im_livechat_channel._open_livechat_mail_channel(anonymous_name='anon 1', previous_operator_id=self.users[0].partner_id.id, user_id=self.users[1].id, country_id=self.env.ref('base.in').id)['id'])
        record_rating = self.env['rating.rating'].create({
            'res_model_id': self.env['ir.model']._get('mail.channel').id,
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
            body="<img src='%s' alt=':%s/5' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s"
            % (record_rating.rating_image_url, record_rating.rating, record_rating.feedback),
            rating_id=record_rating.id,
        )
        self.assertEqual(message.message_format(), [{
            'attachment_ids': [],
            'author': {
                'id': self.users[1].partner_id.id,
                'name': "test1",
            },
            'body': message.body,
            'date': message.date,
            'guestAuthor': [('clear',)],
            'history_partner_ids': [],
            'id': message.id,
            'is_discussion': False,
            'is_note': True,
            'is_notification': False,
            'linkPreviews': [],
            'message_type': 'notification',
            'messageReactionGroups': [],
            'model': 'mail.channel',
            'module_icon': '/mail/static/description/icon.png',
            'needaction_partner_ids': [],
            'notifications': [],
            'rating': {
                'id': record_rating.id,
                'ratingImageUrl': record_rating.rating_image_url,
                'ratingText': record_rating.rating_text,
            },
            'recipients': [],
            'record_name': "test1 Ernest Employee",
            'res_id': channel_livechat_1.id,
            'sms_ids': [],
            'starred_partner_ids': [],
            'subject': False,
            'subtype_description': False,
            'subtype_id': (self.env.ref('mail.mt_note').id, 'Note'),
            'trackingValues': [],
        }])
