# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from markupsafe import Markup

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests.common import users, tagged
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase


@tagged('post_install', '-at_install')
class TestImLivechatMessage(ChatbotCase, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()

    def setUp(self):
        super().setUp()
        self.password = 'Pl1bhD@2!kXZ'
        self.users = self.env['res.users'].create([
            {
                'email': 'e.e@example.com',
                'group_ids': [Command.link(self.env.ref('base.group_user').id)],
                'login': 'emp',
                'password': self.password,
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
            self.env['res.users'].with_user(user).check_access('write')
        user.with_user(user).livechat_username = 'New username'
        self.assertEqual(user.livechat_username, 'New username')

    def test_chatbot_message_format(self):
        self.authenticate(self.users[0].login, self.password)
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "chatbot_script_id": self.chatbot_script.id,
                "persisted": True,
            },
        )
        discuss_channel = self.env['discuss.channel'].browse(data["channel_id"])
        self._post_answer_and_trigger_next_step(
            discuss_channel,
            self.step_dispatch_buy_software.name,
            chatbot_script_answer=self.step_dispatch_buy_software
        )
        chatbot_message = discuss_channel.chatbot_message_ids.mail_message_id[:1]
        self.assertEqual(
            Store().add(chatbot_message).get_result()["mail.message"],
            [
                {
                    "attachment_ids": [],
                    "author_guest_id": False,
                    "author_id": self.chatbot_script.operator_partner_id.id,
                    "body": ["markup", "<p>Can you give us your email please?</p>"],
                    "chatbotStep": {
                        "message": chatbot_message.id,
                        "scriptStep": self.step_email.id,
                    },
                    "create_date": fields.Datetime.to_string(chatbot_message.create_date),
                    "date": fields.Datetime.to_string(chatbot_message.date),
                    "default_subject": "Testing Bot",
                    "email_from": False,
                    "id": chatbot_message.id,
                    "incoming_email_cc": False,
                    "incoming_email_to": False,
                    "message_link_preview_ids": [],
                    "message_type": "comment",
                    "model": "discuss.channel",
                    "needaction": False,
                    "notification_ids": [],
                    "parent_id": False,
                    "partner_ids": [],
                    "pinned_at": False,
                    "rating_id": False,
                    "reactions": [],
                    "record_name": "Testing Bot",
                    "res_id": discuss_channel.id,
                    "scheduledDatetime": False,
                    "starred": False,
                    "thread": {
                        "id": discuss_channel.id,
                        "model": "discuss.channel",
                    },
                    "subject": False,
                    "subtype_id": self.env.ref("mail.mt_comment").id,
                    "trackingValues": [],
                    "write_date": fields.Datetime.to_string(chatbot_message.write_date),
                }
            ],
        )

    @users('emp')
    def test_message_to_store(self):
        im_livechat_channel = self.env['im_livechat.channel'].sudo().create({'name': 'support', 'user_ids': [Command.link(self.users[0].id)]})
        self.env["mail.presence"]._update_presence(self.users[0])
        self.authenticate(self.users[1].login, self.password)
        channel_livechat_1 = self.env["discuss.channel"].browse(
            self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "previous_operator_id": self.users[0].partner_id.id,
                    "channel_id": im_livechat_channel.id,
                },
            )["channel_id"]
        )
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
            Store().add(message).get_result(),
            {
                "mail.message": self._filter_messages_fields(
                    {
                        "attachment_ids": [],
                        "author_guest_id": False,
                        "author_id": self.users[1].partner_id.id,
                        "body": ["markup", message.body],
                        "date": fields.Datetime.to_string(message.date),
                        "write_date": fields.Datetime.to_string(message.write_date),
                        "create_date": fields.Datetime.to_string(message.create_date),
                        "id": message.id,
                        "default_subject": "test1 Ernest Employee",
                        "email_from": '"test1" <test1@example.com>',
                        "incoming_email_cc": False,
                        "incoming_email_to": False,
                        "message_link_preview_ids": [],
                        "message_type": "notification",
                        "reactions": [],
                        "model": "discuss.channel",
                        "needaction": False,
                        "notification_ids": [],
                        "thread": {"id": channel_livechat_1.id, "model": "discuss.channel"},
                        "parent_id": False,
                        "partner_ids": [],
                        "pinned_at": False,
                        "rating_id": record_rating.id,
                        "record_name": "test1 Ernest Employee",
                        "res_id": channel_livechat_1.id,
                        "scheduledDatetime": False,
                        "starred": False,
                        "subject": False,
                        "subtype_id": self.env.ref("mail.mt_note").id,
                        "trackingValues": [],
                    },
                ),
                "mail.message.subtype": [
                    {"description": False, "id": self.env.ref("mail.mt_note").id}
                ],
                "mail.thread": self._filter_threads_fields(
                    {
                        "display_name": "test1 Ernest Employee",
                        "id": channel_livechat_1.id,
                        "model": "discuss.channel",
                        "module_icon": "/mail/static/description/icon.png",
                        "rating_avg": 5.0,
                        "rating_count": 1,
                    },
                ),
                "rating.rating": [
                    {
                        "id": record_rating.id,
                        "rating": 5.0,
                        "rating_image_url": record_rating.rating_image_url,
                        "rating_text": "top",
                    },
                ],
                "res.partner": self._filter_partners_fields(
                    {
                        "avatar_128_access_token": self.users[
                            1
                        ].partner_id._get_avatar_128_access_token(),
                        "id": self.users[1].partner_id.id,
                        "is_company": False,
                        "main_user_id": self.users[1].id,
                        "user_livechat_username": "chuck",
                        "write_date": fields.Datetime.to_string(self.users[1].write_date),
                    },
                ),
                "res.users": self._filter_users_fields(
                    {"id": self.users[1].id, "share": False},
                ),
            },
        )

    @users("portal_test")
    @freeze_time("2020-03-22 10:42:06")
    def test_feedback_message(self):
        """Test posting a feedback message as a portal user, and ensure the proper bus
        notifications are sent."""
        livechat_channel_vals = {"name": "support", "user_ids": [Command.link(self.users[0].id)]}
        im_livechat_channel = self.env["im_livechat.channel"].sudo().create(livechat_channel_vals)
        self.env["mail.presence"]._update_presence(self.users[0])
        self.authenticate(self.env.user.login, self.env.user.login)
        channel = self.env["discuss.channel"].browse(
            self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "previous_operator_id": self.users[0].partner_id.id,
                    "channel_id": im_livechat_channel.id,
                },
            )["channel_id"]
        )

        def _get_feedback_bus():
            message = self.env["mail.message"].sudo().search([], order="id desc", limit=1)
            rating = self.env["rating.rating"].sudo().search([], order="id desc", limit=1)
            return (
                [
                    # channel last interest (not asserted below)
                    (self.env.cr.dbname, "discuss.channel", channel.id),
                    # unread counter/new message separator (not asserted below)
                    (self.env.cr.dbname, "res.partner", self.env.user.partner_id.id),
                    # new_message
                    (self.env.cr.dbname, "discuss.channel", channel.id),
                ],
                [
                    {
                        "type": "discuss.channel/new_message",
                        "payload": {
                            "data": {
                                "mail.message": self._filter_messages_fields(
                                    {
                                        "attachment_ids": [],
                                        "author_guest_id": False,
                                        "author_id": self.env.user.partner_id.id,
                                        "body": [
                                            "markup",
                                            '<div class="o_mail_notification o_hide_author">Rating: <img class="o_livechat_emoji_rating" src="/rating/static/src/img/rating_5.png" alt="rating"><br>\nGood service</div>',
                                        ],
                                        "create_date": fields.Datetime.to_string(
                                            message.create_date
                                        ),
                                        "date": fields.Datetime.to_string(message.date),
                                        "default_subject": "Chell Gladys Ernest Employee",
                                        "id": message.id,
                                        "incoming_email_cc": False,
                                        "incoming_email_to": False,
                                        "message_link_preview_ids": [],
                                        "message_type": "notification",
                                        "model": "discuss.channel",
                                        "parent_id": False,
                                        "partner_ids": [],
                                        "pinned_at": False,
                                        "rating_id": rating.id,
                                        "reactions": [],
                                        "record_name": "Chell Gladys Ernest Employee",
                                        "res_id": channel.id,
                                        "scheduledDatetime": False,
                                        "subject": False,
                                        "subtype_id": self.env.ref("mail.mt_comment").id,
                                        "thread": {"id": channel.id, "model": "discuss.channel"},
                                        "write_date": fields.Datetime.to_string(message.write_date),
                                    },
                                ),
                                "mail.message.subtype": [
                                    {"description": False, "id": self.env.ref("mail.mt_comment").id}
                                ],
                                "mail.thread": self._filter_threads_fields(
                                    {
                                        "display_name": "Chell Gladys Ernest Employee",
                                        "id": channel.id,
                                        "model": "discuss.channel",
                                        "module_icon": "/mail/static/description/icon.png",
                                        "rating_avg": 5.0,
                                        "rating_count": 1,
                                    },
                                ),
                                "rating.rating": [
                                    {
                                        "id": rating.id,
                                        "rating": 5.0,
                                        "rating_image_url": rating.rating_image_url,
                                        "rating_text": "top",
                                    },
                                ],
                                "res.partner": self._filter_partners_fields(
                                    {
                                        "avatar_128_access_token": self.env.user.partner_id._get_avatar_128_access_token(),
                                        "id": self.env.user.partner_id.id,
                                        "is_company": False,
                                        "main_user_id": self.env.user.id,
                                        "name": "Chell Gladys",
                                        "user_livechat_username": False,
                                        "write_date": fields.Datetime.to_string(
                                            self.env.user.write_date
                                        ),
                                    },
                                ),
                                "res.users": self._filter_users_fields(
                                    {"id": self.env.user.id, "share": True},
                                ),
                            },
                            "id": channel.id,
                        },
                    },
                ],
            )

        with self.assertBus(get_params=_get_feedback_bus):
            self.make_jsonrpc_request(
                "/im_livechat/feedback",
                {
                    "channel_id": channel.id,
                    "rate": 5,
                    "reason": "Good service",
                },
            )
