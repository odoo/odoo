# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests import common
from odoo.tests import new_test_user, tagged


@tagged("-at_install", "post_install")
class TestMailMessage(common.MailCommon):
    def test_unlink_failure_message_notify_author(self):
        recipient = new_test_user(self.env, login="Bob", email="invalid_email_addr")
        message = self.env.user.partner_id.message_post(
            body="Hello world!", partner_ids=recipient.partner_id.ids
        )
        self.assertEqual(message.notification_ids.failure_type, "mail_email_invalid")
        self.assertEqual(message.notification_ids.res_partner_id, recipient.partner_id)
        self.assertEqual(message.notification_ids.author_id, self.env.user.partner_id)
        self._reset_bus()
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
