# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged


@tagged("mail_canned_response")
class TestMailCannedResponse(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.canned_responses = cls.env["mail.canned.response"].create([
            {"source": "hello", "substitution": "Hello, how may I help you?"},
            {"source": "bye", "substitution": "Goodbye, have a nice day!"},
        ])

    def test_mail_canned_response_copy(self):
        copied_responses = self.canned_responses.copy()
        self.assertEqual(copied_responses.mapped("source"), ["hello (copy)", "bye (copy)"])

    def test_mail_canned_response_last_used_full_composer(self):
        hello, bye = self.canned_responses
        composer = self.env["mail.compose.message"].create({
            "body": hello.substitution,
            "model": self.partner_employee._name,
            "res_ids": str(self.partner_employee.ids),
        })
        composer.with_context(canned_response_ids=hello.ids).action_send_mail()
        self.canned_responses.invalidate_recordset(["last_used"])
        self.assertTrue(hello.last_used)
        self.assertFalse(bye.last_used)
