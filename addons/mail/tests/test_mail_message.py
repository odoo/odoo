# Part of Odoo. See LICENSE file for full copyright and licensing details.

# from odoo import exceptions
from odoo.addons.mail.tests import common
from odoo.tests import new_test_user, tagged


@tagged("mail_message", "-at_install", "post_install")
class TestMailMessage(common.MailCommon):

    def test_mail_message_read_inexisting(self):
        inexisting_message = self.env['mail.message'].with_user(self.user_employee).browse(-434264)
        self.assertTrue(inexisting_message.check_access_rights('read'), 'Global read right activated')
        self.assertFalse(inexisting_message.exists())
        self.assertEqual(inexisting_message.browse().check_access_rule('read'), None, 'Should not crash (can read void)')
        # TDE to check: cache pollution / inexisting not correctly tracked, ok-ish for stable
        # with self.assertRaises(exceptions.AccessError):
        #     inexisting_message.check_access_rule('read')

    def test_mail_message_read_access(self):
        self.env['res.company'].invalidate_model(['name'])
        message_c1 = self._add_messages(self.env.company, "Company Note 1", author=self.user_employee.partner_id)
        message_c2 = self._add_messages(self.company_2, "Company Note 2", author=self.user_employee_c2.partner_id)
        search_result = self.env["mail.message"].with_context(
            allowed_company_ids=[self.env.company.id]
        ).with_user(self.user_employee).search([("model", "=", "res.company")])
        self.assertIn(message_c1, search_result)
        self.assertNotIn(message_c2, search_result)

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
