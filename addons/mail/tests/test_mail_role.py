# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.website.tools import MockRequest
from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestMailRole(MailCommon, HttpCase):
    def test_post_mention_role(self):
        """Test mention with role"""
        role_discuss = self.env["mail.role"].create({"name": "rd-Discuss"})
        role_js = self.env["mail.role"].create({"name": "rd-JS"})

        user_discuss = mail_new_test_user(
            self.env,
            login="user_d",
            name="Discuss User",
            notification_type="inbox",
            mail_role_ids=[(4, role_discuss.id)],
        )
        user_js = mail_new_test_user(
            self.env,
            login="user_js",
            name="JS User",
            notification_type="inbox",
            mail_role_ids=[(4, role_js.id)],
        )
        user_discuss_js = mail_new_test_user(
            self.env,
            login="user_djs",
            name="Discuss JS User",
            notification_type="inbox",
            mail_role_ids=[(4, role_discuss.id), (4, role_js.id)],
        )

        channel = self.env["discuss.channel"]._create_channel(name="Channel", group_id=None)
        channel.add_members(
            (
                self.partner_employee
                | user_discuss.partner_id
                | user_js.partner_id
                | user_discuss_js.partner_id
            ).ids
        )

        # sending message mentioning roles
        with self.with_user("employee"), MockRequest(self.env):
            messages = [
                ThreadController().mail_message_post(
                    thread_model="discuss.channel",
                    thread_id=channel.id,
                    post_data={
                        "body": "Test",
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                    },
                ),
                ThreadController().mail_message_post(
                    thread_model="discuss.channel",
                    thread_id=channel.id,
                    post_data={
                        "body": "Test @rd-Discuss",
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                        "role_ids": [role_discuss.id],
                    },
                ),
                ThreadController().mail_message_post(
                    thread_model="discuss.channel",
                    thread_id=channel.id,
                    post_data={
                        "body": "Test @rd-JS",
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                        "role_ids": [role_js.id],
                    },
                ),
                ThreadController().mail_message_post(
                    thread_model="discuss.channel",
                    thread_id=channel.id,
                    post_data={
                        "body": "Test @rd-Discuss @rd-JS",
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                        "role_ids": [role_discuss.id, role_js.id],
                    },
                ),
            ]

        notifications = {
            user_discuss.partner_id.id: [
                messages[1]["mail.message"][0]["id"],
                messages[3]["mail.message"][0]["id"],
            ],
            user_js.partner_id.id: [
                messages[2]["mail.message"][0]["id"],
                messages[3]["mail.message"][0]["id"],
            ],
            user_discuss_js.partner_id.id: [
                messages[1]["mail.message"][0]["id"],
                messages[2]["mail.message"][0]["id"],
                messages[3]["mail.message"][0]["id"],
            ],
        }

        for user, msg_ids in notifications.items():
            notif = self.env["mail.notification"].search([("res_partner_id", "=", user)])
            self.assertEqual(
                notif.mail_message_id.ids, msg_ids, f"mentioning roles for user {user}"
            )
