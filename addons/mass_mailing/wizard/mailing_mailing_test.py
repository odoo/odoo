# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class TestMassMailing(models.TransientModel):
    _name = 'mailing.mailing.test'
    _description = 'Sample Mail Wizard'

    email_to = fields.Char(string='Recipients', required=True,
                           help='Comma-separated list of email addresses.', default=lambda self: self.env['mail.message']._get_default_from())
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    def send_mail_test(self):
        self.ensure_one()
        mails = self.env['mail.mail']
        mailing = self.mass_mailing_id
        test_emails = tools.email_split(self.email_to)
        mass_mail_layout = self.env.ref('mass_mailing.mass_mailing_mail_layout')
        for test_mail in test_emails:
            # Convert links in absolute URLs before the application of the shortener
            mailing.write({'body_html': self.env['mail.thread']._replace_local_links(mailing.body_html)})
            body = tools.html_sanitize(mailing.body_html, sanitize_attributes=True, sanitize_style=True)
            mail_values = {
                'email_from': mailing.email_from,
                'reply_to': mailing.reply_to,
                'email_to': test_mail,
                'subject': mailing.subject,
                'body_html': mass_mail_layout.render({'body': body}, engine='ir.qweb', minimal_qcontext=True),
                'notification': True,
                'mailing_id': mailing.id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mails |= mail
        mails.send()
        return True
