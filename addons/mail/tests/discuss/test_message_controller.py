# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.tests import tagged, users
from odoo.tools import mute_logger
from odoo.addons.base.tests.common import HttpCase, HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.http import STATIC_CACHE_LONG
from odoo import Command, fields, http


@odoo.tests.tagged("-at_install", "post_install")
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
                    "filename": "File 1",
                    "name": "File 1",
                    "size": 0,
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
                    "filename": "File 1",
                    "name": "File 1",
                    "size": 0,
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
                    "filename": "File 2",
                    "name": "File 2",
                    "size": 0,
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
                    "filename": "File 1",
                    "name": "File 1",
                    "size": 0,
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
                    "filename": "File 2",
                    "name": "File 2",
                    "size": 0,
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
                        "partner_emails": ["john2@test.be", "john3@test.be"],  # Both emails in one request
                        "partner_additional_values": {
                            "john2@test.be": {'phone': '123456789'},  # Original partner
                            "john3 <john3@test.be>": {'phone': '987654321'}  # Name-Addr formatted partner
                        },
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
        self.assertEqual(
            1,
            self.env["res.partner"].search_count([('email', '=', "john3@test.be"), ('phone', '=', "987654321")]),
            "additional_values should be handled correctly when using keys in name_addr format",
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


@tagged("mail_message")
class TestMessageLinks(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_employee_1 = mail_new_test_user(cls.env, login='tao1', groups='base.group_user', name='Tao Lee')
        cls.public_channel = cls.env['discuss.channel'].channel_create(name='Public Channel1', group_id=None)
        cls.private_group = cls.env['discuss.channel'].create_group(partners_to=cls.user_employee_1.partner_id.ids, name="Group")

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
            self.assertEqual(res.status_code, 401)

    @users('employee')
    def test_message_link_by_public(self):
        message = self.public_channel.message_post(
            body='Public Channel Message',
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )
        res = self.url_open(f'/mail/message/{message.id}')
        self.assertEqual(res.status_code, 200)
