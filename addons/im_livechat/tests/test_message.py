# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import Command
from odoo.tests.common import users, tagged, HttpCase


@tagged('post_install', '-at_install')
class TestImLivechatMessage(HttpCase):
    def setUp(self):
        super().setUp()
        self.password = 'Pl1bhD@2!kXZ'
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
            {'name': 'test1', 'login': 'test1', 'password': self.password, 'email': 'test1@example.com'},
        ])

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
            'attachment_ids': [],
            'author': {
                'id': self.users[1].partner_id.id,
                'is_company': self.users[1].partner_id.is_company,
                'name': "test1",
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
            'messageReactionGroups': [],
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
