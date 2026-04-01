# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestResRole(MailCommon, HttpCase):
    def test_post_mention_role(self):
        """Test mention with role"""
        contact = self.env["res.partner"].create({"name": "A contact"})
        role_discuss = self.env["res.role"].create({"name": "rd-Discuss"})
        role_js = self.env["res.role"].create({"name": "rd-JS"})
        user_discuss = mail_new_test_user(
            self.env,
            login="user_d",
            name="Discuss User",
            notification_type="inbox",
            role_ids=[Command.link(role_discuss.id)],
        )
        user_js = mail_new_test_user(
            self.env,
            login="user_js",
            name="JS User",
            notification_type="inbox",
            role_ids=[Command.link(role_js.id)],
        )
        user_discuss_js = mail_new_test_user(
            self.env,
            login="user_djs",
            name="Discuss JS User",
            notification_type="inbox",
            role_ids=[Command.link(role_discuss.id), Command.link(role_js.id)],
        )
        self.authenticate("employee", "employee")
        for [roles, expected_users] in [
            (self.env["res.role"], self.env["res.users"]),
            (role_discuss, user_discuss + user_discuss_js),
            (role_js, user_js + user_discuss_js),
            (role_discuss + role_js, user_discuss + user_js + user_discuss_js),
        ]:
            data = self.make_jsonrpc_request(
                "/mail/message/post",
                {
                    "thread_model": "res.partner",
                    "thread_id": contact.id,
                    "post_data": {
                        "body": "irrelevant",
                        "message_type": "comment",
                        "role_ids": roles.ids,
                        "subtype_xmlid": "mail.mt_note",
                    },
                },
            )
            message = next(filter(lambda m: m["id"] == data["message_id"], data["store_data"]["mail.message"]))
            self.assertEqual(
                message["partner_ids"],
                expected_users.partner_id.ids
            )
