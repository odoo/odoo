# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.tools import mute_logger, date_utils
from odoo.tests import HttpCase
from odoo.http import STATIC_CACHE_LONG
from odoo import Command


@odoo.tests.tagged("-at_install", "post_install")
class TestMessageController(HttpCase):
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
    def test_channel_message_attachments(self):
        self.authenticate(None, None)
        self.opener.cookies[
            self.guest._cookie_name
        ] = f"{self.guest.id}{self.guest._cookie_separator}{self.guest.access_token}"
        # test message post: token error
        res1 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "attachment_ids": [self.attachments[0].id],
                            "attachment_tokens": ["wrong token"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertIn(
            f"The attachment {self.attachments[0].id} does not exist or you do not have the rights to access it",
            res1.text,
            "guest should not be allowed to add attachment without token when posting message",
        )
        # test message post: token ok
        res2 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "attachment_ids": [self.attachments[0].id],
                            "attachment_tokens": [self.attachments[0].access_token],
                            "message_type": "comment",
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res2.status_code, 200)
        message_format1 = res2.json()["result"]
        self.assertEqual(
            message_format1["attachments"],
            json.loads(json.dumps(self.attachments[0]._attachment_format(), default=date_utils.json_default)),
            "guest should be allowed to add attachment with token when posting message",
        )
        # test message update: token error
        res3 = self.url_open(
            url="/mail/message/update_content",
            data=json.dumps(
                {
                    "params": {
                        "message_id": message_format1["id"],
                        "body": "test",
                        "attachment_ids": [self.attachments[1].id],
                        "attachment_tokens": ["wrong token"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertIn(
            f"The attachment {self.attachments[1].id} does not exist or you do not have the rights to access it",
            res3.text,
            "guest should not be allowed to add attachment without token when updating message",
        )
        # test message update: token ok
        res4 = self.url_open(
            url="/mail/message/update_content",
            data=json.dumps(
                {
                    "params": {
                        "message_id": message_format1["id"],
                        "body": "test",
                        "attachment_ids": [self.attachments[1].id],
                        "attachment_tokens": [self.attachments[1].access_token],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res4.status_code, 200)
        message_format2 = res4.json()["result"]
        self.assertEqual(
            message_format2["attachments"],
            json.loads(json.dumps(self.attachments.sorted("id")._attachment_format(), default=date_utils.json_default)),
            "guest should be allowed to add attachment with token when updating message",
        )
        # test message update: own attachment ok
        res5 = self.url_open(
            url="/mail/message/update_content",
            data=json.dumps(
                {
                    "params": {
                        "message_id": message_format2["id"],
                        "body": "test",
                        "attachment_ids": [self.attachments[1].id],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res5.status_code, 200)
        message_format3 = res5.json()["result"]
        self.assertEqual(
            message_format3["attachments"],
            json.loads(json.dumps(self.attachments.sorted("id")._attachment_format(), default=date_utils.json_default)),
            "guest should be allowed to add own attachment without token when updating message",
        )

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
        self.authenticate(None, None)
        self.opener.cookies[
            self.guest._cookie_name
        ] = f"{self.guest.id}{self.guest._cookie_separator}{self.guest.access_token}"
        res1 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(
            0,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "guest should not be allowed to create a partner from an email",
        )
        res2 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john@test.be"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(
            0,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "guest should not be allowed to create a partner from an email from message_post",
        )
        demo = self.authenticate("demo", "demo")
        res3 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "emails": ["john@test.be"],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "authenticated users can create a partner from an email",
        )
        # should not create another partner with same email
        res4 = self.url_open(
            url="/mail/partner/from_email",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
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
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john2@test.be"],
                        },
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john2@test.be")]),
            "authenticated users can create a partner from an email from message_post",
        )
        # should not create another partner with same email
        res6 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.channel._name,
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "partner_emails": ["john2@test.be"],
                        },
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

    def test_mail_cache_control_header(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [Command.set([self.ref('base.group_portal')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        test_user = self.authenticate("testuser", "testuser")
        partner = self.env["res.users"].browse(test_user.uid).partner_id
        self.channel.add_members(testuser.partner_id.ids)
        res = self.url_open(
            url=f"/discuss/channel/{self.channel.id}/avatar_128?unique={self.channel._get_avatar_cache_key()}"
        )
        self.assertEqual(res.headers["Cache-Control"], f"public, max-age={STATIC_CACHE_LONG}")

        res = self.url_open(
            url=f"/discuss/channel/{self.channel.id}/avatar_128"
        )
        self.assertEqual(res.headers["Cache-Control"], "no-cache")

        res = self.url_open(
            url=f"/discuss/channel/{self.channel.id}/partner/{partner.id}/avatar_128?unique={partner.write_date.isoformat()}"
        )
        self.assertEqual(res.headers["Cache-Control"], f"public, max-age={STATIC_CACHE_LONG}")

        res = self.url_open(
            url=f"/discuss/channel/{self.channel.id}/partner/{partner.id}/avatar_128"
        )
        self.assertEqual(res.headers["Cache-Control"], "no-cache")

        res = self.url_open(
            url=f"/discuss/channel/{self.channel.id}/guest/{self.guest.id}/avatar_128?unique={self.guest.write_date.isoformat()}"
        )
        self.assertEqual(res.headers["Cache-Control"], f"public, max-age={STATIC_CACHE_LONG}")

        res = self.url_open(
            url=f"/discuss/channel/{self.channel.id}/guest/{self.guest.id}/avatar_128"
        )
        self.assertEqual(res.headers["Cache-Control"], "no-cache")
