# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.http import STATIC_CACHE_LONG
from odoo import Command, fields


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
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
    def test_channel_message_attachments(self):
        self.authenticate(None, None)
        self.opener.cookies[self.guest._cookie_name] = self.guest._format_auth_cookie()
        # test message post: token error
        res1 = self.url_open(
            url="/mail/message/post",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "attachment_ids": [self.attachments[0].id],
                        },
                    },
                    "attachment_tokens": ["wrong token"],
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
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                            "attachment_ids": [self.attachments[0].id],
                            "message_type": "comment",
                        },
                        "attachment_tokens": [self.attachments[0].access_token],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res2.status_code, 200)
        data1 = res2.json()["result"]
        self.assertEqual(
            data1["ir.attachment"],
            [
                    {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[0].create_date),
                    "id": self.attachments[0].id,
                    "name": "File 1",
                    "res_name": "Test channel",
                    "mimetype": "application/octet-stream",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "voice": False,
                    'type': 'binary',
                    'url': False,
                },
            ],
            "guest should be allowed to add attachment with token when posting message",
        )
        # test message update: token error
        res3 = self.url_open(
            url="/mail/message/update_content",
            data=json.dumps(
                {
                    "params": {
                        "message_id": data1["mail.message"][0]["id"],
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
                        "message_id": data1["mail.message"][0]["id"],
                        "body": "test",
                        "attachment_ids": [self.attachments[1].id],
                        "attachment_tokens": [self.attachments[1].access_token],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res4.status_code, 200)
        data2 = res4.json()["result"]
        self.assertEqual(
            data2["ir.attachment"],
            [
                {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[0].create_date),
                    "id": self.attachments[0].id,
                    "name": "File 1",
                    "res_name": "Test channel",
                    "mimetype": "application/octet-stream",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "voice": False,
                    'type': 'binary',
                    'url': False,
                },
                {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[1].create_date),
                    "id": self.attachments[1].id,
                    "name": "File 2",
                    "res_name": "Test channel",
                    "mimetype": "application/octet-stream",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "voice": False,
                    'type': 'binary',
                    'url': False,
                },
            ],
            "guest should be allowed to add attachment with token when updating message",
        )
        # test message update: own attachment ok
        res5 = self.url_open(
            url="/mail/message/update_content",
            data=json.dumps(
                {
                    "params": {
                        "message_id": data2["mail.message"][0]["id"],
                        "body": "test",
                        "attachment_ids": [self.attachments[1].id],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res5.status_code, 200)
        data3 = res5.json()["result"]
        self.assertEqual(
            data3["ir.attachment"],
            [
                {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[0].create_date),
                    "id": self.attachments[0].id,
                    "name": "File 1",
                    "res_name": "Test channel",
                    "mimetype": "application/octet-stream",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "voice": False,
                    'type': 'binary',
                    'url': False,
                },
                {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[1].create_date),
                    "id": self.attachments[1].id,
                    "name": "File 2",
                    "res_name": "Test channel",
                    "mimetype": "application/octet-stream",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "voice": False,
                    'type': 'binary',
                    'url': False,
                },
            ],
            "guest should be allowed to add own attachment without token when updating message",
        )

    @mute_logger("odoo.addons.http_routing.models.ir_http", "odoo.http")
    def test_mail_partner_from_email_unauthenticated(self):
        self.authenticate(None, None)
        self.opener.cookies[self.guest._cookie_name] = self.guest._format_auth_cookie()
        res1 = self.url_open(
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
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(
            0,
            self.env["res.partner"].search_count([('email', '=', "john@test.be")]),
            "guest should not be allowed to create a partner from an email",
        )

        self.authenticate(None, None)
        self.opener.cookies[self.guest._cookie_name] = self.guest._format_auth_cookie()
        res1 = self.url_open(
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
                        "thread_model": "discuss.channel",
                        "thread_id": self.channel.id,
                        "post_data": {
                            "body": "test",
                        },
                        "partner_emails": ["john@test.be"],
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
            url=f"/web/image/?field=avatar_128&id={self.channel.id}&model=discuss.channel&unique={self.channel.avatar_cache_key}"
        )
        self.assertIn(f"max-age={STATIC_CACHE_LONG}", res.headers["Cache-Control"])

        res = self.url_open(
            url=f"/web/image/?field=avatar_128&id={self.channel.id}&model=discuss.channel"
        )
        self.assertIn("no-cache", res.headers["Cache-Control"])

        res = self.url_open(
            url=f"/web/image?field=avatar_128&id={partner.id}&model=res.partner&unique={fields.Datetime.to_string(partner.write_date)}"
        )
        self.assertIn(f"max-age={STATIC_CACHE_LONG}", res.headers["Cache-Control"])

        res = self.url_open(
            url=f"/web/image?field=avatar_128&id={partner.id}&model=res.partner"
        )
        self.assertIn("no-cache", res.headers["Cache-Control"])

        res = self.url_open(
            url=f"/web/image?field=avatar_128&id={self.guest.id}&model=mail.guest&unique={fields.Datetime.to_string(partner.write_date)}"
        )
        self.assertIn(f"max-age={STATIC_CACHE_LONG}", res.headers["Cache-Control"])

        res = self.url_open(
            url=f"/web/image?field=avatar_128&id={self.guest.id}&model=mail.guest"
        )
        self.assertIn("no-cache", res.headers["Cache-Control"])
