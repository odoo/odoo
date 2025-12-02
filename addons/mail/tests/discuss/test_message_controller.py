# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.tests import tagged, users
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCase, HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
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
                        "name": "File 1",
                        "res_id": 0,
                        "res_model": "mail.compose.message",
                    },
                    {
                        "name": "File 2",
                        "res_id": 0,
                        "res_model": "mail.compose.message",
                    },
                ]
            )
        )
        cls.guest = cls.env["mail.guest"].create({"name": "Guest"})
        cls.channel._add_members(guests=cls.guest)

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
                            "attachment_tokens": ["wrong token"],
                        },
                    },
                },
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertIn(
            "One or more attachments do not exist, or you do not have the rights to access them.",
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
                            "attachment_tokens": [self.attachments[0]._get_ownership_token()],
                            "message_type": "comment",
                        },
                    },
                },
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res2.status_code, 200)
        data1 = res2.json()["result"]
        self.assertEqual(
            data1["store_data"]["ir.attachment"],
            [
                {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[0].create_date),
                    "file_size": 0,
                    "has_thumbnail": False,
                    "id": self.attachments[0].id,
                    "mimetype": "application/octet-stream",
                    "name": "File 1",
                    "ownership_token": self.attachments[0]._get_ownership_token(),
                    "raw_access_token": self.attachments[0]._get_raw_access_token(),
                    "res_name": "Test channel",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "thumbnail_access_token": self.attachments[0]._get_thumbnail_token(),
                    "voice_ids": [],
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
                        "message_id": data1["message_id"],
                        "update_data": {
                            "body": "test",
                            "attachment_ids": [self.attachments[1].id],
                            "attachment_tokens": ["wrong token"],
                        },
                    },
                },
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertIn(
            "One or more attachments do not exist, or you do not have the rights to access them.",
            res3.text,
            "guest should not be allowed to add attachment without token when updating message",
        )
        # test message update: token ok
        res4 = self.url_open(
            url="/mail/message/update_content",
            data=json.dumps(
                {
                    "params": {
                        "message_id": data1["message_id"],
                        "update_data": {
                            "body": "test",
                            "attachment_ids": [self.attachments[1].id],
                            "attachment_tokens": [self.attachments[1]._get_ownership_token()],
                        },
                    },
                },
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
                    "file_size": 0,
                    "has_thumbnail": False,
                    "id": self.attachments[0].id,
                    "mimetype": "application/octet-stream",
                    "name": "File 1",
                    "ownership_token": self.attachments[0]._get_ownership_token(),
                    "raw_access_token": self.attachments[0]._get_raw_access_token(),
                    "res_name": "Test channel",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "thumbnail_access_token": self.attachments[0]._get_thumbnail_token(),
                    "voice_ids": [],
                    'type': 'binary',
                    'url': False,
                },
                {
                    "checksum": False,
                    "create_date": fields.Datetime.to_string(self.attachments[1].create_date),
                    "file_size": 0,
                    "has_thumbnail": False,
                    "id": self.attachments[1].id,
                    "mimetype": "application/octet-stream",
                    "name": "File 2",
                    "ownership_token": self.attachments[1]._get_ownership_token(),
                    "raw_access_token": self.attachments[1]._get_raw_access_token(),
                    "res_name": "Test channel",
                    "thread": {"id": self.channel.id, "model": "discuss.channel"},
                    "thumbnail_access_token": self.attachments[1]._get_thumbnail_token(),
                    "voice_ids": [],
                    'type': 'binary',
                    'url': False,
                },
            ],
            "guest should be allowed to add attachment with token when updating message",
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
                            "partner_emails": ["john@test.be"],
                        },
                    },
                },
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
            'group_ids': [Command.set([self.ref('base.group_portal')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        test_user = self.authenticate("testuser", "testuser")
        partner = self.env["res.users"].browse(test_user.uid).partner_id
        self.channel._add_members(users=testuser)
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


@tagged("mail_message")
class TestMessageLinks(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_employee_1 = mail_new_test_user(cls.env, login='tao1', groups='base.group_user', name='Tao Lee')
        cls.public_channel = cls.env['discuss.channel']._create_channel(name='Public Channel1', group_id=None)
        cls.private_group = cls.env['discuss.channel']._create_group(partners_to=cls.user_employee_1.partner_id.ids, name="Group")

    @users('employee')
    def test_message_link_by_employee(self):
        channel_message = self.public_channel.message_post(body='Public Channel Message', message_type='comment')
        private_message_id = self.private_group.with_user(self.user_employee_1).message_post(
            body='Private Message',
            message_type='comment',
        ).id
        self.authenticate('employee', 'employee')
        with self.subTest(channel_message=channel_message):
            expected_url = self.base_url() + f'/odoo/action-mail.action_discuss?active_id={channel_message.res_id}&highlight_message_id={channel_message.id}'
            res = self.url_open(f'/mail/message/{channel_message.id}')
            self.assertEqual(res.url, expected_url)
        with self.subTest(private_message_id=private_message_id):
            res = self.url_open(f'/mail/message/{private_message_id}')
            self.assertEqual(res.status_code, 404)

    @users('employee')
    def test_message_link_by_public(self):
        message = self.public_channel.message_post(
            body='Public Channel Message',
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )
        res = self.url_open(f'/mail/message/{message.id}')
        self.assertEqual(res.status_code, 200)
