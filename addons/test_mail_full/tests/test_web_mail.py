from odoo.addons.mail.tests import common
from odoo.tests import tagged


@tagged("mail_message", "-at_install", "post_install")
class TestWebMail(common.MailCommon):

    def test_message_web_search_read(self):
        """Tests than when doing web_search_read on mail.message, even if we don't get enough records
        to fill the limit, we still get the "correct" amount of total records
        """
        self.env['mail.message'].search([]).unlink()
        self.env['mail.message'].create([{
            'subject': 'Messages that should be displayed when searching',
            'message_type': 'email',
            'author_id': self.user_employee.partner_id.id,
            'date': '2026-04-30'
        } for _ in range(10)])
        self.env['mail.message'].create([{
            'subject': 'Messages that should NOT be displayed when searching',
            'message_type': 'email',
            'author_id': self.user_employee_c2.partner_id.id,
            'date': '2026-05-01'
        } for _ in range(2)])
        search_result = self.env['mail.message'].with_user(self.user_employee).web_search_read([], {'date': {}}, 0, 4, 'date DESC')
        self.assertEqual(len(search_result['records']), 2)
        self.assertEqual(search_result['length'], 10)
