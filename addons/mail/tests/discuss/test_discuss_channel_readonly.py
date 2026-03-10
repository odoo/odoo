# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo.addons.mail.tests.discuss.discuss_common import DiscussCommon
from odoo.exceptions import UserError, AccessError
from odoo.fields import Command
from odoo.tests.common import HttpCase, JsonRpcException, freeze_time, users
from odoo.tools.misc import mute_logger


class TestDiscussChannelReadonly(DiscussCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_mail_common()
        cls._setup_alice()
        cls.test_channel = cls.env["discuss.channel"].create(
            {
                "name": "Read-only Channel",
                "channel_type": "channel",
                "is_readonly": True,
                "channel_member_ids": [
                    Command.create({"partner_id": cls.alice_partner.id}),
                    Command.create(
                        {"partner_id": cls.partner_employee.id, "channel_role": "owner"},
                    ),
                ],
            },
        )

    def test_only_admin_can_set_readonly(self):
        alice_member = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", self.test_channel.id),
                ("partner_id", "=", self.alice_partner.id),
            ],
        )
        self.assertFalse(alice_member.channel_role)
        employee_member = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", self.test_channel.id),
                ("partner_id", "=", self.partner_employee.id),
            ],
        )
        self.assertEqual(employee_member.channel_role, "owner")
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.alice_user).is_readonly = False
        self.test_channel.with_user(self.user_employee).is_readonly = False
        self.test_channel.with_user(self.alice_user).is_readonly = False  # existing value, no raise
        self.assertFalse(self.test_channel.is_readonly)
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.alice_user).is_readonly = True
        self.test_channel.with_user(self.user_employee).is_readonly = True
        self.test_channel.with_user(self.alice_user).is_readonly = True  # existing value, no raise
        self.assertTrue(self.test_channel.is_readonly)

    @users("employee")
    def test_readonly_channel_no_join_call(self):
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/mail/rtc/channel/join_call",
                {"channel_id": self.test_channel.id},
            )

    @users("employee")
    def test_readonly_channel_admin_can_post_comment(self):
        self.assertEqual(self.test_channel.self_member_id.channel_role, "owner")
        message = self.test_channel.message_post(
            body="Admin message in read-only channel",
            message_type="comment",
        )
        self.assertEqual(str(message.body), "<p>Admin message in read-only channel</p>")

    def test_readonly_channel_user_cannot_post_comment(self):
        alice_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.alice_partner.id),
        ])
        self.assertFalse(alice_member.channel_role)
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.alice_user).message_post(
                body="User message in read-only channel",
                message_type="comment",
            )

    def test_readonly_channel_user_cannot_post_notification_message(self):
        alice_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.alice_partner.id),
        ])
        self.assertFalse(alice_member.channel_role)
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.alice_user).message_post(
                body="User message in read-only channel",
            )

    @freeze_time("2026-01-01 12:00:00")
    def test_readonly_channel_user_can_edit_own_message(self):
        self.test_channel.is_readonly = False
        message = self.test_channel.with_user(self.alice_user).message_post(
            body="Original message", message_type="comment"
        )
        self.test_channel.is_readonly = True
        self.authenticate(self.alice_user.login, self.alice_user.password)
        self.make_jsonrpc_request(
            "/mail/message/update_content",
            {
                "message_id": message.id,
                "update_data": {"body": "<p>Edited message</p>"},
            },
        )
        self.assertEqual(
            str(message.body),
            '<p>Edited message <span class="o-mail-Message-edited" '
            'data-o-datetime="2026-01-01 12:00:00"></span></p>',
        )

    def test_readonly_channel_user_can_star_message(self):
        self.authenticate(self.alice_user.login, self.alice_user.password)
        message = self.test_channel.message_post(body="Message to star")
        self.make_jsonrpc_request(
            "/mail/action", {"fetch_params": [["add_bookmark", {"message_id": message.id}]]},
        )
        self.assertIn(self.alice_partner, message.bookmarked_partner_ids)

    def test_readonly_channel_user_can_react(self):
        message = self.test_channel.message_post(body="Message to react")
        self.authenticate(self.alice_user.login, self.alice_user.password)
        self.make_jsonrpc_request(
            "/mail/message/reaction",
            {
                "message_id": message.id,
                "content": "❤️",
                "action": "add",
            },
        )
        self.assertTrue(
            message.reaction_ids.filtered(
                lambda r: r.partner_id == self.alice_partner and r.content == "❤️",
            ),
        )

    def test_readonly_channel_admin_can_create_subchannel(self):
        employee_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.partner_employee.id),
        ])
        self.assertEqual(employee_member.channel_role, "owner")
        message = self.test_channel.message_post(body="Message to create subchannel")
        self.authenticate(self.user_employee.login, self.user_employee.password)
        self.make_jsonrpc_request(
            "/discuss/channel/sub_channel/create",
            {
                "parent_channel_id": self.test_channel.id,
                "from_message_id": message.id,
                "name": "Subchannel created by user",
            },
        )
        subchannel = self.env["discuss.channel"].search(
            [
                ("name", "=", "Subchannel created by user"),
                ("parent_channel_id", "=", self.test_channel.id),
                ("from_message_id", "=", message.id),
            ],
        )
        self.assertFalse(subchannel.is_readonly)

    @mute_logger("odoo.http")
    def test_readonly_channel_user_cannot_create_subchannel(self):
        alice_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.alice_partner.id),
        ])
        self.assertFalse(alice_member.channel_role)
        message = self.test_channel.message_post(body="Message to create subchannel")
        self.authenticate(self.alice_user.login, self.alice_user.password)
        with self.assertRaises(JsonRpcException) as cm:
            self.make_jsonrpc_request(
                "/discuss/channel/sub_channel/create",
                {
                    "parent_channel_id": self.test_channel.id,
                    "from_message_id": message.id,
                    "name": "Subchannel created by user",
                },
            )
        self.assertTrue(cm.exception, AccessError)

    def test_readonly_channel_user_cannot_pin_message(self):
        alice_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.alice_partner.id),
        ])
        self.assertFalse(alice_member.channel_role)
        message = self.test_channel.message_post(body="Message to pin")
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.alice_user).set_message_pin(message.id, True)
        self.test_channel.with_user(self.user_employee).set_message_pin(message.id, True)
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.alice_user).set_message_pin(message.id, False)
        self.test_channel.with_user(self.user_employee).set_message_pin(message.id, True)

    def test_readonly_channel_user_cannnot_create_message(self):
        alice_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.alice_partner.id),
        ])
        self.assertFalse(alice_member.channel_role)
        with self.assertRaises(UserError):
            self.env["mail.message"].with_user(self.alice_user).create(
                {
                    "body": "Message created by user",
                    "model": "discuss.channel",
                    "res_id": self.test_channel.id,
                    "author_id": self.alice_partner.id,
                },
            )

    def test_readonly_channel_admin_can_create_message(self):
        employee_member = self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.test_channel.id), ("partner_id", "=", self.partner_employee.id),
        ])
        self.assertEqual(employee_member.channel_role, "owner")
        message = (
            self.env["mail.message"]
            .with_user(self.user_employee)
            .create(
                {
                    "body": "Message created by admin",
                    "model": "discuss.channel",
                    "res_id": self.test_channel.id,
                    "author_id": self.user_employee.partner_id.id,
                },
            )
        )
        self.assertEqual(message.body, Markup("<p>Message created by admin</p>"))
