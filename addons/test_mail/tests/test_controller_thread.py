import json

from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install", "mail_controller")
class TestMessageController(HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create(
            {
                "group_public_id": None,
                "name": "Test channel",
            }
        )
        cls.public_user = cls.env.ref("base.public_user")
        cls.attachments = (
            cls.env["ir.attachment"]
            .with_user(cls.public_user)
            .sudo()
            .create(
                [
                    {
                        "access_token": cls.env["ir.attachment"]._generate_access_token(),
                        "name": "File 1",
                        "res_id": 0,
                        "res_model": "mail.compose.message",
                    },
                    {
                        "access_token": cls.env["ir.attachment"]._generate_access_token(),
                        "name": "File 2",
                        "res_id": 0,
                        "res_model": "mail.compose.message",
                    },
                ]
            )
        )
        cls.guest = cls.env["mail.guest"].create({"name": "Guest"})
        cls.channel.add_members(guest_ids=cls.guest.ids)

    @mute_logger("odoo.addons.http_routing.models.ir_http", "odoo.http")
    def test_attachment_hijack(self):
        att = self.env["ir.attachment"].create(
            [
                {
                    "name": "arguments_for_firing_marc_demo",
                    "res_id": 0,
                    "res_model": "mail.compose.message",
                },
            ]
        )
        demo = self.authenticate("demo", "demo")
        channel = self.env["discuss.channel"].create({"group_public_id": None, "name": "public_channel"})
        channel.add_members(
            self.env["res.users"].browse(demo.uid).partner_id.ids
        )  # don't care, we just need a channel where demo is follower
        no_access_request = self.url_open("/web/content/" + str(att.id))
        self.assertFalse(
            no_access_request.ok
        )  # if this test breaks, it might be due to a change in /web/content, or the default rules for accessing an attachment. This is not an issue but it makes this test irrelevant.
        response = self.url_open(
            url="/mail/message/post",
            headers={"Content-Type": "application/json"},  # route called as demo
            data=json.dumps(
                {
                    "params": {
                        "post_data": {
                            "attachment_ids": [att.id],  # demo does not have access to this attachment id
                            "body": "",
                            "message_type": "comment",
                            "partner_ids": [],
                            "subtype_xmlid": "mail.mt_comment",
                        },
                        "thread_id": channel.id,
                        "thread_model": "discuss.channel",
                    }
                },
            ),
        )
        self.assertNotIn(
            "arguments_for_firing_marc_demo", response.text
        )  # demo should not be able to see the name of the document

    @mute_logger("odoo.addons.http_routing.models.ir_http", "odoo.http")
    def test_mail_partner_from_email_authenticated(self):
        demo = self.authenticate("demo", "demo")
        res3 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "emails": ["john@test.be"],
                        'additional_values': {"john@test.be": {'phone': '123456789'}},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be"), ('phone', '=', "123456789")]),
            "authenticated users can create a partner from an email",
        )
        # should not create another partner with same email
        res4 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "'mail/partner/from_email' does not create another user if there's already a user with matching email",
        )
        self.channel.add_members(
            self.env["res.users"].browse(demo.uid).partner_id.ids # so demo can post message
        )
        res5 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                        },
                        "partner_emails": ["john2@test.be"],
                        "partner_additional_values": {"john2@test.be": {'phone': '123456789'}},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be"), ('phone', '=', "123456789")]),
            "authenticated users can create a partner from an email from message_post",
        )
        # should not create another partner with same email
        res6 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                        },
                        "partner_emails": ["john2@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res6.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be")]),
            "'mail/message/post' does not create another user if there's already a user with matching email",
        )

    def test_chatter_on_archived_record(self):
        self.authenticate("admin", "admin")
        archived_partner = self.env["res.partner"].create({"name": "partner", "active": False})

        # 1. posting a message
        data = self.make_jsonrpc_request("/mail/message/post", {
            "thread_model": "res.partner",
            "thread_id": archived_partner.id,
            "post_data": {
                "body": "A great message",
            }
        })
        self.assertIn("A great message", data["mail.message"][0]["body"])

        # 2. attach a file
        response = self.url_open(
            "/mail/attachment/upload",
            {
                "csrf_token": http.Request.csrf_token(self),
                "thread_id": archived_partner.id,
                "thread_model": "res.partner",
            },
            files={"ufile": b""},
        )
        self.assertEqual(response.status_code, 200)
