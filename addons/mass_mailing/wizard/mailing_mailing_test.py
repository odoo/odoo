# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, fields, models, tools


class TestMassMailing(models.TransientModel):
    _name = 'mailing.mailing.test'
    _description = 'Sample Mail Wizard'

    email_to = fields.Text(string='Recipients', required=True,
                           help='Carriage-return-separated list of email addresses.', default=lambda self: self.env.user.email_formatted)
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    def send_mail_test(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.pop('default_state', None)
        self = self.with_context(ctx)

        mails_sudo = self.env['mail.mail'].sudo()
        valid_emails = []
        invalid_candidates = []
        for candidate in self.email_to.splitlines():
            test_email = tools.email_split(candidate)
            if test_email:
                valid_emails.append(test_email[0])
            else:
                invalid_candidates.append(candidate)

        mailing = self.mass_mailing_id
        record = self.env[mailing.mailing_model_real].search([], limit=1)

        # If there is atleast 1 record for the model used in this mailing, then we use this one to render the template
        # Downside: Qweb syntax is only tested when there is atleast one record of the mailing's model
        if record:
            # Returns a proper error if there is a syntax error with Qweb
            body = mailing.with_context(preserve_comments=True)._render_field('body_html', record.ids, post_process=True)[record.id]
            preview = mailing._render_field('preview', record.ids, post_process=True)[record.id]
            full_body = mailing._prepend_preview(Markup(body), preview)
            subject = mailing._render_field('subject', record.ids)[record.id]
        else:
            full_body = mailing._prepend_preview(mailing.body_html, mailing.preview)
            subject = mailing.subject

        # Convert links in absolute URLs before the application of the shortener
        full_body = self.env['mail.render.mixin']._replace_local_links(full_body)

        for valid_email in valid_emails:
            mail_values = {
                'email_from': mailing.email_from,
                'reply_to': mailing.reply_to,
                'email_to': valid_email,
                'subject': subject,
                'body_html': self.env['ir.qweb']._render('mass_mailing.mass_mailing_mail_layout', {'body': full_body}, minimal_qcontext=True),
                'is_notification': True,
                'mailing_id': mailing.id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'auto_delete': False,  # they are manually deleted after notifying the document
                'mail_server_id': mailing.mail_server_id.id,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mails_sudo |= mail
        mails_sudo.send()

        notification_messages = []
        if invalid_candidates:
            notification_messages.append(
                _('Mailing addresses incorrect: %s', ', '.join(invalid_candidates)))

        for mail_sudo in mails_sudo:
            if mail_sudo.state == 'sent':
                notification_messages.append(
                    _('Test mailing successfully sent to %s', mail_sudo.email_to))
            elif mail_sudo.state == 'exception':
                notification_messages.append(
                    _('Test mailing could not be sent to %s:<br>%s',
                        mail_sudo.email_to,
                        mail_sudo.failure_reason)
                )

        # manually delete the emails since we passed 'auto_delete: False'
        mails_sudo.unlink()

        if notification_messages:
            self.mass_mailing_id._message_log(body='<ul>%s</ul>' % ''.join(
                ['<li>%s</li>' % notification_message for notification_message in notification_messages]
            ))

        return True
