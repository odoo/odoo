from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestFetchmail(object):
    def test_simulate_malformed_message_leaves_no_trace(self):
        before = self.env['ir.attachment'].search([], count=True)
        with mute_logger('odoo.addons.fetchmail.models.fetchmail'):
            self.server.with_context(__fail_message=True).fetch_mail()
        after = self.env['ir.attachment'].search([], count=True)
        self.assertEqual(before, after)

    def test_new_message(self):
        before = self.env['mail.message'].search([], count=True)
        self.server.fetch_mail()
        after = self.env['mail.message'].search([], count=True)
        self.assertEqual(before + 1, after)


class TestEmailsPOP(TransactionCase, TestFetchmail):
    def setUp(self):
        super(TestEmailsPOP, self).setUp()
        server = self.env['fetchmail.server'].create({
            'name': 'pop',
            'state': 'done',
            'type': 'pop',
        })
        self.server = server.with_context(__mock_me=True)


class TestEmailsIMAP(TransactionCase, TestFetchmail):
    def setUp(self):
        super(TestEmailsIMAP, self).setUp()
        server = self.env['fetchmail.server'].create({
            'name': ' imap',
            'state': 'done',
            'type': 'imap',
        })
        self.server = server.with_context(__mock_me=True)
