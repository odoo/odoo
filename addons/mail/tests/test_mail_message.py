# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.models import mail_message as mail_message_module
from odoo.addons.mail.tests import common
from odoo.tests import HttpCase, new_test_user, tagged, users

from unittest.mock import patch


@tagged("mail_message")
class TestMailMessage(common.MailCommon, HttpCase):

    @users("employee")
    def test_can_star_message_without_write_access(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        message = self.env["mail.message"].sudo().create({
            "author_id": self.partner_admin.id,
            "model": "res.partner",
            "res_id": self.partner_admin.id,
            "body": "Hey this is me!",
        })
        message = message.sudo(False)
        self.env.user.group_ids -= self.env.ref("base.group_partner_manager")
        self.assertFalse(message.has_access("write"))
        self.make_jsonrpc_request(
            "/mail/store", {"fetch_params": [["add_bookmark", {"message_id": message.id}]]},
        )
        self.assertIn(self.env.user.partner_id, message.bookmarked_partner_ids)
        self.make_jsonrpc_request("/mail/store", {"fetch_params": ["remove_all_bookmarks"]})
        self.assertNotIn(self.env.user.partner_id, message.bookmarked_partner_ids)

    def test_mail_message_read_inexisting(self):
        user = new_test_user(self.env, login="Bob", email="bob@test.com")
        inexisting_message = self.env['mail.message'].with_user(user).browse(-434264)
        self.assertFalse(inexisting_message.exists())
        self.assertTrue(inexisting_message.browse().has_access('read'))
        self.assertFalse(inexisting_message.has_access('read'))

    def test_web_push_attachment_body(self):
        image = self.env["ir.attachment"].create(
            {"mimetype": "image/png", "name": "picture.png", "raw": b"image"}
        )
        voice = self.env["ir.attachment"].create(
            {"mimetype": "audio/mpeg", "name": "recording.mp3", "raw": b"voice"}
        )
        voice._set_voice_metadata()
        pdf = self.env["ir.attachment"].create(
            {"mimetype": "application/pdf", "name": "quote.pdf", "raw": b"pdf"}
        )
        cases = [
            ([image], "📷\N{NO-BREAK SPACE} picture.png"),
            ([voice], "🎤\N{NO-BREAK SPACE} Voice Message"),
            ([pdf], "📄\N{NO-BREAK SPACE} quote.pdf"),
            ([image, voice], "📷\N{NO-BREAK SPACE} picture.png and Voice Message"),
            ([image, voice, pdf], "📷\N{NO-BREAK SPACE} picture.png and 2 other attachments"),
        ]
        for attachments, expected_body in cases:
            with self.subTest(count=len(attachments), first=attachments[0].name):
                message = self.env.user.partner_id.message_post(
                    body="",
                    attachment_ids=[a.id for a in attachments],
                )
                payload = self.env.user.partner_id._notify_by_web_push_prepare_payload(message)
                self.assertEqual(payload["options"]["body"], expected_body)

    def test_mail_message_read_access(self):
        self.env['res.company'].invalidate_model(['name'])
        message_c1 = self._add_messages(self.env.company, "Company Note 1", author=self.user_employee.partner_id)
        message_c2 = self._add_messages(self.company_2, "Company Note 2", author=self.user_employee_c2.partner_id)
        message_not_author_but_in_to = self._add_messages(
            self.company_2, "Company Note 3",
            author=self.user_employee_c2.partner_id, partner_ids=self.user_employee.partner_id)
        message_not_author_but_in_cc = self._add_messages(
            self.company_2, "Company Note 4",
            author=self.user_employee_c2.partner_id, partner_cc_ids=self.user_employee.partner_id)
        message_not_author_nor_in_recipients = self._add_messages(
            self.company_2, "Company Note 5",
            author=self.user_employee_c2.partner_id, partner_cc_ids=self.user_employee_c3.partner_id)
        search_result = (
            self.env["mail.message"]
            .with_context(allowed_company_ids=[self.env.company.id])
            .with_user(self.user_employee)
            .search([("model", "=", "res.company")])
        )
        self.assertIn(message_c1, search_result)
        self.assertNotIn(message_c2, search_result)
        self.assertIn(message_not_author_but_in_to, search_result)
        self.assertIn(message_not_author_but_in_cc, search_result)
        self.assertNotIn(message_not_author_nor_in_recipients, search_result)

    def test_mail_message_read_access_search_with_limit(self):
        ids = []
        ids += self._add_messages(self.env.company, "Accessible notes", count=5).ids
        ids += self._add_messages(self.company_2, "Inccessible notes", count=5).ids
        ids += self._add_messages(self.env.company, "Accessible notes", count=5).ids
        messages = (self.env["mail.message"]
            .with_user(self.user_employee)
            .with_context(allowed_company_ids=[self.env.company.id])
        ).browse(ids)
        accessible = messages._filtered_access('read')
        self.assertEqual(len(accessible), 10)
        domain = [('id', 'in', ids)]

        self.assertEqual(messages.search(domain, limit=100), accessible)
        self.assertEqual(messages.sudo().search(domain, limit=100), messages)

        Message = self.registry[messages._name]
        with (
            patch.object(mail_message_module, 'IN_MAX', 3),
            patch.object(Message, '_search', autospec=True, side_effect=Message._search) as search_func,
        ):
            self.assertEqual(messages.search(domain, limit=100), accessible)
            self.assertGreaterEqual(search_func.call_count, 4)

    @users("employee")
    def test_unlink_failure_message_notify_author(self):
        recipient = new_test_user(self.env(su=True), login="Bob", email="invalid_email_addr")
        with self.mock_mail_gateway():
            message = self.env.user.partner_id.message_post(
                body="Hello world!", partner_ids=recipient.partner_id.ids
            )
        self.assertEqual(message.notification_ids.failure_type, "mail_email_invalid")
        self.assertEqual(message.notification_ids.res_partner_id, recipient.partner_id)
        self.assertEqual(message.notification_ids.author_id, self.env.user.partner_id)
        with self.assertBus(
            [
                BusResult(recipient, "mail.message/delete", {"message_ids": [message.id]}),
                BusResult(self.env.user, "mail.message/delete", {"message_ids": [message.id]}),
            ],
        ):
            message.unlink()
