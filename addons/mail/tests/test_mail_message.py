# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests import common
from odoo.tests import new_test_user, tagged, users


@tagged("-at_install", "post_install", "mail_message")
class TestMailMessage(common.MailCommon):
    @users("employee")
    def test_can_star_message_without_write_access(self):
        message = self.env["mail.message"].sudo().create({
            "author_id": self.partner_admin.id,
            "model": "res.partner",
            "res_id": self.partner_admin.id,
            "body": "Hey this is me!",
        })
        message = message.sudo(False)
        self.env.user.group_ids -= self.env.ref("base.group_partner_manager")
        self.assertFalse(message.has_access("write"))
        message.toggle_message_starred()
        self.assertIn(self.env.user.partner_id, message.starred_partner_ids)
        self.env["mail.message"].unstar_all()
        self.assertNotIn(self.env.user.partner_id, message.starred_partner_ids)

    def test_unlink_failure_message_notify_author(self):
        recipient = new_test_user(self.env, login="Bob", email="invalid_email_addr")
        with self.mock_mail_gateway():
            message = self.env.user.partner_id.message_post(
                body="Hello world!", partner_ids=recipient.partner_id.ids
            )
        self.assertEqual(message.notification_ids.failure_type, "mail_email_invalid")
        self.assertEqual(message.notification_ids.res_partner_id, recipient.partner_id)
        self.assertEqual(message.notification_ids.author_id, self.env.user.partner_id)
        with self.assertBus(
            [
                (self.cr.dbname, "res.partner", recipient.partner_id.id),
                (self.cr.dbname, "res.partner", self.env.user.partner_id.id),
            ],
            [
                {"type": "mail.message/delete", "payload": {"message_ids": [message.id]}},
                {"type": "mail.message/delete", "payload": {"message_ids": [message.id]}},
            ],
        ):
            message.unlink()
