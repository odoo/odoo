# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger


class TestResRole(MailCommon, HttpCase):
    def test_store_res_role_internal_users_only(self):
        role = self.env["res.role"].create({"name": "rd-Discuss"})
        mail_new_test_user(self.env, login="user_d", role_ids=[Command.link(role.id)])
        fetch_params = {"fetch_params": [["res.role", {"id": role.id}]]}
        self.authenticate("employee", "employee")
        data = self.make_jsonrpc_request("/mail/store", fetch_params)
        self.assertEqual(data["res.role"], [{"id": role.id, "name": "rd-Discuss", "user_ids_count": 1}])
        portal_user = mail_new_test_user(self.env, login="portal_d", groups="base.group_portal")
        self.authenticate(portal_user.login, portal_user.login)
        with mute_logger("odoo.addons.mail.tools.store_handler"):
            data = self.make_jsonrpc_request("/mail/store", fetch_params)
        self.assertEqual(data, {})

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
