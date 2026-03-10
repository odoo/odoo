# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import random

from odoo import fields
from odoo.fields import Command
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


class TestWebsiteLivechatCommon(TestImLivechatCommon, TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_mail_common()
        cls._setup_livechat_common()
        cls.maxDiff = None
        cls.env.company.email = "test@test.example.com"
        base_datetime = fields.Datetime.from_string("2019-11-11 21:30:00")
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_livechat_user = cls.env.ref("im_livechat.im_livechat_group_user")
        cls.operator = cls.env["res.users"].create(
            {
                "name": "Operator Michel",
                "login": "operator",
                "email": "operator@example.com",
                "password": "ideboulonate",
                "livechat_username": "El Deboulonnator",
                "group_ids": [Command.set([cls.group_user.id, cls.group_livechat_user.id])],
            },
        )
        cls.livechat_channel.write(
            {"name": "The basic channel", "user_ids": [Command.set([cls.operator.id])]},
        )
        cls.env.ref("website.default_website").channel_id = cls.livechat_channel.id
        visitor_vals = {
            "lang_id": cls.env.ref("base.lang_en").id,
            "country_id": cls.env.ref("base.be").id,
            "website_id": cls.env.ref("website.default_website").id,
        }
        max_sessions_per_operator = 5
        cls.visitors = cls.env["website.visitor"].create(
            [
                {
                    "lang_id": cls.env.ref("base.lang_en").id,
                    "country_id": cls.env.ref("base.de").id,
                    "website_id": cls.env.ref("website.default_website").id,
                    "partner_id": cls.partner_demo.id,
                    "access_token": cls.user_demo.partner_id.id,
                },
            ]
            + [
                dict(visitor_vals, access_token="%032x" % random.randrange(16**32))
                for _ in range(max_sessions_per_operator)
            ],
        )
        cls.visitor_demo, cls.visitor = cls.visitors[0], cls.visitors[1]
        cls.page_1, cls.page_2 = cls.env["website.page"].create(
            [
                {
                    "name": "Test Page 1",
                    "type": "qweb",
                    "url": "/page_1",
                    "website_id": cls.env.ref("website.default_website").id,
                },
                {
                    "name": "Test Page 2",
                    "type": "qweb",
                    "url": "/page_2",
                    "website_id": cls.env.ref("website.default_website").id,
                },
            ],
        )
        cls.track_ids = cls.env["website.track"].create(
            [
                {
                    "page_id": cls.page_1.id,
                    "visitor_id": cls.visitor.id,
                    "visit_datetime": base_datetime - datetime.timedelta(minutes=20),
                },
                {
                    "page_id": cls.page_2.id,
                    "visitor_id": cls.visitor.id,
                    "visit_datetime": base_datetime - datetime.timedelta(minutes=10),
                },
                {
                    "page_id": cls.page_1.id,
                    "visitor_id": cls.visitor.id,
                    "visit_datetime": base_datetime,
                },
            ],
        )

        cls.livechat_base_url = cls.livechat_channel.get_base_url()
        cls.open_chat_url = f"{cls.livechat_base_url}/im_livechat/get_session"
        cls.open_chat_params = {"params": {"channel_id": cls.livechat_channel.id}}
        cls.send_feedback_url = f"{cls.livechat_base_url}/im_livechat/feedback"
        cls.leave_session_url = f"{cls.livechat_base_url}/im_livechat/visitor_leave_session"
        cls.env["mail.presence"]._update_presence(cls.operator)

    def setUp(self):
        super().setUp()
        # override the _get_visitor_from_request to return self.visitor
        self.target_visitor = self.visitor
        def get_visitor_from_request(self_mock, **kwargs):
            return self.target_visitor
        self.patch(type(self.env['website.visitor']), '_get_visitor_from_request', get_visitor_from_request)

    def _send_message(self, channel, email_from, body, author_id=False):
        # As bus is unavailable in test mode, we cannot call /mail/message/post route to post a message.
        # Instead, we post directly the message on the given channel.
        channel.with_context(mail_post_autofollow_author_skip=True) \
            .message_post(author_id=author_id, email_from=email_from, body=body,
                          message_type='comment', subtype_id=self.env.ref('mail.mt_comment').id)

    def _send_rating(self, channel, visitor, rating_value, reason=False):
        channel_messages_count = len(channel.message_ids)

        rating_to_emoji = {1: "😞", 3: "😐", 5: "😊"}
        self.url_open(url=self.send_feedback_url, json={'params': {
            'channel_id': channel.id,
            'rate': rating_value,
            'reason': reason,
        }})
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', channel._name)], limit=1).id
        rating = self.env['rating.rating'].search([('res_id', '=', channel.id), ('res_model_id', '=', res_model_id)])
        self.assertEqual(rating.rating, rating_value, "The rating is not correct.")
        self.assertEqual(len(channel.message_ids), channel_messages_count + 1)
