# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class TestMassMailing(models.TransientModel):
    _name = 'mail.mass_mailing.test'
    _description = 'Sample Mail Wizard'

    email_to = fields.Char(string='Recipients', required=True,
        help='Comma-separated list of email addresses.', default=lambda self: self.env['mail.message']._get_default_from())
    mass_mailing_id = fields.Many2one('mail.mass_mailing', 'Mailing', required=True)

    @api.multi
    def send_mail_test(self):
        self.ensure_one()
        Mail = self.env['mail.mail']
        mailing = self.mass_mailing_id
        test_emails = tools.email_split(self.email_to)
        mail_ids = []
        for test_mail in test_emails:
            mail_values = {
                'email_from': mailing.email_from,
                'reply_to': mailing.reply_to,
                'email_to': test_mail,
                'subject': mailing.name,
                'body_html': '',
                'notification': True,
                'mailing_id': mailing.id,
            }
            mail = Mail.create(mail_values)
            unsubscribe_url = mail._get_unsubscribe_url(test_mail)
            body = tools.append_content_to_html(mailing.body_html, unsubscribe_url, plaintext=False, container_tag='p')
            mail.body_html = mailing.body_html
            mail_ids.append(mail.id)
        Mail.send(mail_ids)
        return True
