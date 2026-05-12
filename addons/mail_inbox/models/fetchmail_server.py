# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import email
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class FetchmailServer(models.Model):
    _inherit = 'fetchmail.server'

    is_inbox = fields.Boolean(
        'Use as Personal Inbox',
        help='When enabled, fetched emails are stored as inbox records instead of '
             'being routed into Odoo documents.',
    )
    user_id = fields.Many2one(
        'res.users', 'Owner',
        default=lambda self: self.env.user,
        help='User who owns this inbox. Only they can see its messages.',
    )

    def _process_fetched_message(self, message_env, message):
        if not self.is_inbox:
            return super()._process_fetched_message(message_env, message)

        # Convert raw bytes to EmailMessage for parsing
        if isinstance(message, bytes):
            msg_email = email.message_from_bytes(message, policy=email.policy.SMTP)
        else:
            msg_email = email.message_from_string(message, policy=email.policy.SMTP)

        msg_dict = message_env['mail.thread'].message_parse(msg_email)
        attachment_ids = self._create_mail_attachments(message_env, msg_dict.pop('attachments', []))

        message_env['fetchmail.mail'].create({
            'fetchmail_server_id': self.id,
            'email_from': msg_dict.get('email_from', ''),
            'email_to': msg_dict.get('to', ''),
            'email_cc': msg_dict.get('cc', ''),
            'subject': msg_dict.get('subject', ''),
            'body': msg_dict.get('body', ''),
            'date': msg_dict.get('date') or fields.Datetime.now(),
            'attachment_ids': [(6, 0, attachment_ids)],
            'mail_type': 'incoming',
            'mail_status': 'new',
        })

    def _create_mail_attachments(self, message_env, attachments):
        """Create ir.attachment records from parsed email attachments."""
        if not attachments:
            return []
        vals_list = []
        for attachment in attachments:
            name = attachment[0] if attachment else 'attachment'
            content = attachment[1] if len(attachment) > 1 else b''
            mimetype = attachment[2] if len(attachment) > 2 else 'application/octet-stream'
            if hasattr(content, 'as_bytes'):
                content = content.as_bytes()
            elif isinstance(content, str):
                content = content.encode()
            if not isinstance(content, bytes):
                continue
            vals_list.append({
                'name': name or 'attachment',
                'datas': base64.b64encode(content).decode(),
                'mimetype': mimetype or 'application/octet-stream',
            })
        return message_env['ir.attachment'].create(vals_list).ids
