# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.tools.misc import file_open


class TestMassMailing(models.TransientModel):
    _name = 'mailing.mailing.test'
    _description = 'Sample Mail Wizard'

    email_to = fields.Text(string='Recipients', required=True, default=lambda s: s._get_email_to(),
                           help='Carriage-return-separated list of email addresses.')
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    @api.model
    def _get_success_test_mailing_message(self):
        return 'Test mailing successfully sent to'

    @api.model
    def _get_failure_test_mailing_message(self):
        return 'Test mailing could not be sent to'

    def _get_email_to(self):
        """
        Tries to get the last test email adress used from the chatter logged notes. If not
        available, returns the current user's email adress.
        """
        if not self.env.context.get('default_mass_mailing_id'):
            return self.env.user.email_formatted

        chatter_test_message = self.env['mail.message'].search([
            ('model', '=', 'mailing.mailing'),
            ('res_id', '=', self.env.context['default_mass_mailing_id']),
            ('message_type', '=', 'notification'),
            '|',
                ('body', 'ilike', self._get_success_test_mailing_message()),
                ('body', 'ilike', self._get_failure_test_mailing_message()),
        ], order='id desc', limit=1)
        email_adresses = None

        if chatter_test_message:
            email_adresses = re.findall(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', str(chatter_test_message.body))

        return '\n'.join(email_adresses) if email_adresses else self.env.user.email_formatted

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
            # do not force lang, will simply use user context
            body = mailing._render_field('body_html', record.ids, compute_lang=False)[record.id]
            preview = mailing._render_field('preview', record.ids, compute_lang=False)[record.id]
            full_body = mailing._prepend_preview(Markup(body), preview)
            subject = mailing._render_field('subject', record.ids, compute_lang=False)[record.id]
        else:
            full_body = mailing._prepend_preview(mailing.body_html, mailing.preview)
            subject = mailing.subject
        subject = f'[TEST] {subject}'

        # Convert links in absolute URLs before the application of the shortener
        full_body = self.env['mail.render.mixin']._replace_local_links(full_body)

        with file_open("mass_mailing/static/src/scss/mass_mailing_mail.scss", "r") as fd:
            styles = fd.read()
        for valid_email in valid_emails:
            mail_values = {
                'email_from': mailing.email_from,
                'reply_to': mailing.reply_to,
                'email_to': valid_email,
                'subject': subject,
                'body_html': self.env['ir.qweb']._render('mass_mailing.mass_mailing_mail_layout', {
                    'body': full_body,
                    'mailing_style': Markup(f'<style>{styles}</style>'),
                }, minimal_qcontext=True),
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
                    _(f'{self._get_success_test_mailing_message()} {mail_sudo.email_to}'))
            elif mail_sudo.state == 'exception':
                notification_messages.append(
                    _(f'{self._get_failure_test_mailing_message()} {mail_sudo.email_to}:') +
                    (Markup("<br/>") + mail_sudo.failure_reason)
                )

        # manually delete the emails since we passed 'auto_delete: False'
        mails_sudo.unlink()

        if notification_messages:
            self.mass_mailing_id._message_log(body=Markup('<ul>%s</ul>') % ''.join(
                [Markup('<li>%s</li>') % notification_message for notification_message in notification_messages]
            ))

        return True
