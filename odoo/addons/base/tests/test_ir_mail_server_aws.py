import os

from unittest.mock import patch

from odoo import modules
from odoo.tools import formataddr
from odoo.tests import TransactionCase, tagged


@tagged('-standard', 'external')
class TestIrMailServerAWS(TransactionCase):
    RE_MESSAGE_ID = r'<[0-9a-f]{16}-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-\d{6}@[a-z]{2}-[a-z]+-\d\.amazonses\.com>$'

    def test_message_id(self):
        self.assertRegex('<010f019fddd6aa1e-a4a9432d-c933-40f8-be0b-f471852851af-000000@us-west-2.amazonses.com>', self.RE_MESSAGE_ID)

    def test_send(self):
        self.env['ir.mail_server'].create({
            'name': 'AWS SES SMTP',
            'smtp_encryption': 'ssl',
            'smtp_host': os.environ['AWS_SES_SMTP_HOST'],
            'smtp_user': os.environ['AWS_SES_SMTP_USER'],
            'smtp_pass': os.environ['AWS_SES_SMTP_PASS'],
            'smtp_port': 465,
        })

        mail = self.env['mail.mail'].create({
            'body': 'body_ses_smtp',
            'email_from': formataddr(['AWS_SES_SMTP_FROM', os.environ['AWS_SES_SMTP_FROM']]),
            'email_to': [formataddr(['SUCCESS', 'success@simulator.amazonses.com'])],
            'subject': 'subject_ses_smtp',
        })
        self.assertIn('openerp-private', mail.message_id)
        with patch.object(modules.module, 'current_test', False):
            mail.send(raise_exception=True)
        self.assertRegex(mail.message_id, self.RE_MESSAGE_ID)
