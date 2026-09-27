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
