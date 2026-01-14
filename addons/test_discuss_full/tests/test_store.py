from markupsafe import Markup

from odoo import fields, Command
from odoo.tests.common import HttpCase, users
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store


class TestStoreFull(MailCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.password = "Pl1bhD@2!kXZ"
        self.users = self.env["res.users"].create(
            [
                {
                    "email": "e.e@example.com",
                    "group_ids": [Command.link(self.env.ref("base.group_user").id)],
                    "login": "emp",
                    "password": self.password,
                    "name": "Ernest Employee",
                    "notification_type": "inbox",
                    "odoobot_state": "disabled",
                    "signature": "--\nErnest",
                },
                {
                    "email": "test1@example.com",
                    "login": "test1",
                    "name": "test1",
                    "password": self.password,
                },
            ]
        )
        settings = self.env["res.users.settings"]._find_or_create_for_user(self.users[1])
        settings.livechat_username = "chuck"
        self.maxDiff = None

    @users("emp")
    def test_store_add_message(self):
        im_livechat_channel = (
            self.env["im_livechat.channel"]
            .sudo()
            .create({"name": "support", "user_ids": [Command.link(self.users[0].id)]})
        )
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
        record_rating = self.env["rating.rating"].create(
            {
                "res_model_id": self.env["ir.model"]._get("discuss.channel").id,
                "res_id": channel_livechat_1.id,
                "parent_res_model_id": self.env["ir.model"]._get("im_livechat.channel").id,
                "parent_res_id": im_livechat_channel.id,
                "rated_partner_id": self.users[0].partner_id.id,
                "partner_id": self.users[1].partner_id.id,
                "rating": 5,
                "consumed": True,
            }
        )
        message = channel_livechat_1.message_post(
            author_id=record_rating.partner_id.id,
            body=Markup(
                "<img src='%s' alt=':%s/5' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s"
            )
            % (record_rating.rating_image_url, record_rating.rating, record_rating.feedback),
            rating_id=record_rating.id,
        )
        self.assertEqual(
            Store().add(message, "_store_message_fields").get_result(),
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
