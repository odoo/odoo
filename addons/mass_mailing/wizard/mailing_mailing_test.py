# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.utils import getaddresses
from markupsafe import Markup

from odoo import _, api, fields, models, tools


class MailingMailingTest(models.TransientModel):
    _name = 'mailing.mailing.test'
    _description = 'Sample Mail Wizard'
    # allow mailing.mailing.test records to live for 10h (instead of 1h default)
    # used for quality of life in combination with '_default_email_to'
    _transient_max_hours = 10.0

    def _default_email_to(self):
        """ Fetch the last used 'email_to' to populate the email_to value, fallback to user email.
         This enables a user to do quick successive tests without having to type it every time.
         As this is a transient model, it will not always work, but is sufficient as just a default
         value. """
        return self.env['mailing.mailing.test'].search([
            ('create_uid', '=', self.env.uid),
        ], order='create_date desc', limit=1).email_to or self.env.user.email_formatted

    def _get_model_selection(self):
        """ Return mailing enabled models to use in selection values.
        It will act like a list of allowed models for Reference field. """
        result = self.env['ir.model'].sudo().search([('is_mailing_enabled', '=', True)])
        return [(model.model, model.name) for model in result]

    email_to = fields.Text(string='Recipients', required=True, default=_default_email_to)
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')
    email_from = fields.Char(string='From', compute='_compute_mailing_preview')
    subject = fields.Char(string='Subject', compute='_compute_mailing_preview')
    preview_text = fields.Char(string='Preview Text', compute='_compute_mailing_preview')
    reply_to = fields.Char(string='Reply To', compute='_compute_mailing_preview')
    body_html = fields.Html(string='Preview Body', compute='_compute_mailing_preview', sanitize='email_outgoing')
    preview_record_ref = fields.Reference(
        string='Preview for',
        compute='_compute_preview_record_ref',
        readonly=False,
        selection='_get_model_selection',
        store=True,
    )

    @api.depends('mass_mailing_id')
    def _compute_preview_record_ref(self):
        to_reset = self.filtered(lambda t: not t.mass_mailing_id.mailing_model_real)
        if to_reset:
            to_reset.preview_record_ref = False

        for test in (self - to_reset):
            mailing = test.mass_mailing_id
            res = self.env[mailing.mailing_model_real].search([], limit=1)
            test.preview_record_ref = f'{mailing.mailing_model_real},{res.id}' if res else False

    @api.depends('mass_mailing_id', 'preview_record_ref')
    def _compute_mailing_preview(self):
        to_reset = self.filtered(lambda t: not t.mass_mailing_id)
        if to_reset:
            to_reset.update({
                'email_from': False,
                'subject': False,
                'body_html': False,
                'preview_text': False,
                'reply_to': False,
            })

        for record in (self - to_reset):
            mailing = record.mass_mailing_id
            if record.preview_record_ref:
                composer_values = {
                    'composition_mode': 'mass_mail',
                    'model': mailing.mailing_model_real,
                    'email_from': mailing.email_from,
                    'subject': mailing.subject,
                    'body': mailing.body_html,
                }
                composer = self.env['mail.compose.message'].with_context(
                    default_email_from=mailing.email_from,
                ).new(composer_values)
                mail_values = composer._prepare_mail_values(record.preview_record_ref.ids)[record.preview_record_ref.id]
                record.email_from = mail_values['email_from']
                record.reply_to = mail_values['reply_to']
                record.subject = mail_values['subject']
                record.body_html = mail_values['body_html']
                record.preview_text = mailing._render_field('preview', record.preview_record_ref.ids)[record.preview_record_ref.id]
            else:
                record.email_from = mailing.email_from
                record.reply_to = mailing.reply_to
                record.subject = mailing.subject
                record.body_html = mailing.body_html
                record.preview_text = mailing.preview

    def send_mail_test(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.pop('default_state', None)
        self = self.with_context(ctx)

        mails_sudo = self.env['mail.mail'].sudo()
        valid_emails = []
        invalid_candidates = []
        for line in self.email_to.splitlines():
            for name, email in getaddresses([line]):
                test_email = tools.email_split(email)
                if test_email:
                    valid_emails.append(test_email[0])
                else:
                    invalid_candidates.append(email or name)

        mailing = self.mass_mailing_id
        body = mailing._prepend_preview(self.body_html or '', self.preview_text)
        subject = _('[TEST] %(mailing_subject)s', mailing_subject=self.subject)

        for valid_email in valid_emails:
            mail_values = {
                'email_from': self.email_from,
                'reply_to': self.reply_to,
                'email_to': valid_email,
                'subject': subject,
                'body_html': body,
                'is_notification': True,
                'mailing_id': mailing.id,
                'attachment_ids': [
                    (4, attachment.id) for attachment in mailing.attachment_ids
                ],
                'auto_delete': False,  # they are manually deleted after notifying the document
                'mail_server_id': mailing.mail_server_id.id,
            }
            if self.preview_record_ref:
                mail_values['model'] = self.preview_record_ref._name
                mail_values['res_id'] = self.preview_record_ref.id

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mails_sudo |= mail
        mails_sudo.with_context({'mailing_test_mail': True}).send()

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
                    _('Test mailing could not be sent to %s:', mail_sudo.email_to) +
                    (Markup("<br/>") + mail_sudo.failure_reason)
                )

        success_count = len(mails_sudo.filtered(lambda m: m.state == 'sent'))
        # manually delete the emails since we passed 'auto_delete: False'
        mails_sudo.unlink()

        if notification_messages:
            self.mass_mailing_id._message_log(body=Markup('<ul>%s</ul>') % Markup().join(
                [Markup('<li>%s</li>') % notification_message for notification_message in notification_messages]
            ))

        total = len(valid_emails) + len(invalid_candidates)
        failed_count = total - success_count
        if failed_count > 0:
            notif_message = _(
                'Test mailing successfully sent to %(success)s recipients, and %(failed)s failed.',
                success=success_count, failed=failed_count,
            )
        else:
            notif_message = _(
                'Test mailing successfully sent to %(success)s recipients.',
                success=success_count,
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': notif_message,
            },
        }
