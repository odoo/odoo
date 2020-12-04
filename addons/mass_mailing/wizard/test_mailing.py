# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class TestMassMailing(models.TransientModel):
    _name = 'mail.mass_mailing.test'
    _description = 'Sample Mail Wizard'

    email_to = fields.Char(string='Recipients', required=True,
                           help='Comma-separated list of email addresses.', default=lambda self: self.env['mail.message']._get_default_from())
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mailing', required=True, ondelete='cascade')

    @api.multi
    def send_mail_test(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.pop('default_state', None)
        self = self.with_context(ctx)

        mails = self.env['mail.mail']
        mailing = self.mass_mailing_id
        test_emails = tools.email_split(self.email_to)
        mass_mail_layout = self.env.ref('mass_mailing.mass_mailing_mail_layout')

        record = self.env[mailing.mailing_model_real].search([], limit=1)
        body = mailing.body_html
        subject = mailing.subject

        # If there is atleast 1 record for the model used in this mailing, then we use this one to render the template
        # Downside: Jinja syntax is only tested when there is atleast one record of the mailing's model
        if record:
            # Returns a proper error if there is a syntax error with jinja
            body = self.env['mail.template']._render_template(body, mailing.mailing_model_real, record.ids, post_process=True)[record.id]
            subject = self.env['mail.template']._render_template(subject, mailing.mailing_model_real, record.ids)[record.id]

        # Convert links in absolute URLs before the application of the shortener
        body = self.env['mail.thread']._replace_local_links(body)
        body = tools.html_sanitize(body, sanitize_attributes=True, sanitize_style=True)

        for test_mail in test_emails:
            mail_values = {
                'email_from': mailing.email_from,
                'reply_to': mailing.reply_to,
                'email_to': test_mail,
                'subject': subject,
                'body_html': mass_mail_layout.render({'body': body}, engine='ir.qweb', minimal_qcontext=True),
                'notification': True,
                'mailing_id': mailing.id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'auto_delete': True,
                'mail_server_id': mailing.mail_server_id.id,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mails |= mail
        mails.send()
        return True
