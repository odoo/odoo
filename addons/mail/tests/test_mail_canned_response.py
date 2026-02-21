# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged


@tagged("mail_canned_response")
class TestMailCannedResponse(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.canned_response = cls.env["mail.canned.response"].create({
            "source": "hello",
            "substitution": "Hello, how may I help you?",
        })

    def test_mail_canned_response_copy(self):
        copied = self.canned_response.copy()
        self.assertEqual(copied.source, f"{self.canned_response.source} (copy)")
