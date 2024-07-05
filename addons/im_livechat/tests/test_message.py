# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests.common import users, tagged, HttpCase
from odoo.addons.mail.tools.discuss import Store


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
            {
                "email": "test1@example.com",
                "login": "test1",
                "name": "test1",
                "password": self.password,
            },
        ])
        settings = self.env["res.users.settings"]._find_or_create_for_user(self.users[1])
        settings.livechat_username = "chuck"
        self.maxDiff = None

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

    @users('emp')
    def test_message_to_store(self):
        im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.env['bus.presence'].create({'user_id': self.users[0].id, 'status': 'online'})  # make available for livechat (ignore leave)
        self.authenticate(self.users[1].login, self.password)
        channel_livechat_1 = self.env['discuss.channel'].browse(self.make_jsonrpc_request("/im_livechat/get_session", {
            'anonymous_name': 'anon 1',
            'previous_operator_id': self.users[0].partner_id.id,
            'country_id': self.env.ref('base.in').id,
            'channel_id': im_livechat_channel.id,
        })["Thread"][0]['id'])
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
        self.assertEqual(
            Store(message, for_current_user=True).get_result(),
            {
                "Message": [
                    {
                        "attachments": [],
                        "author": {"id": self.users[1].partner_id.id, "type": "partner"},
                        "body": message.body,
                        "date": message.date,
                        "write_date": message.write_date,
                        "create_date": message.create_date,
                        "id": message.id,
                        "default_subject": "test1 Ernest Employee",
                        "is_discussion": False,
                        "is_note": True,
                        "linkPreviews": [],
                        "message_type": "notification",
                        "reactions": [],
                        "model": "discuss.channel",
                        "needaction": False,
                        "notifications": [],
                        "thread": {"id": channel_livechat_1.id, "model": "discuss.channel"},
                        "parentMessage": False,
                        "pinned_at": False,
                        "rating": {
                            "id": record_rating.id,
                            "ratingImageUrl": record_rating.rating_image_url,
                            "ratingText": "top",
                        },
                        "recipients": [],
                        "record_name": "test1 Ernest Employee",
                        "res_id": channel_livechat_1.id,
                        "scheduledDatetime": False,
                        "starred": False,
                        "subject": False,
                        "subtype_description": False,
                        "trackingValues": [],
                    },
                ],
                "Persona": [
                    {
                        "id": self.users[1].partner_id.id,
                        "is_company": False,
                        "isInternalUser": True,
                        "type": "partner",
                        "user_livechat_username": "chuck",
                        "userId": self.users[1].id,
                        "write_date": fields.Datetime.to_string(self.users[1].write_date),
                    },
                ],
                "Thread": [
                    {
                        "id": channel_livechat_1.id,
                        "model": "discuss.channel",
                        "module_icon": "/mail/static/description/icon.png",
                    },
                ],
            },
        )
