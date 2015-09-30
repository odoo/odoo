# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from openerp import _, api, fields, models

_logger = logging.getLogger(__name__)


class IrMail_Server(models.Model):
    _inherit = 'ir.mail_server'

    use_smtp_quota = fields.Boolean('SMTP Mail Quota')
    smtp_quota_seconds = fields.Integer('Time Frame (Seconds)')
    smtp_quota_limit = fields.Integer('Quantity')
    mail_log_ids = fields.One2many('mail.log.sent', 'mail_server_id', string="Sent Mails")

    @api.multi
    def _handle_smtp_quota(self, default=False):
        """Get currently available quantity in case a quota is configured!

           :param mail_server: Defined outgoing mail server.
           :param optional: Indicate that the mail server is default
        """
        self.ensure_one()
        process_datetime = datetime.utcnow()
        quota_frame = process_datetime - timedelta(seconds=self.smtp_quota_seconds)
        domain = [
            ('date', '>=', quota_frame.strftime('%Y-%m-%d %H:%M:%S')),
            ('mail_server_id', '=', self.id)
        ]
        sent_mails = 0
        for log in self.mail_log_ids.search(domain):
            sent_mails += log.nbr_recipients
        return self.smtp_quota_limit - sent_mails

    @api.multi
    def _get_mails_quota_aware(self, mails, default=False):
        """Check whether there is a mail quota set and add the maximum of
           mails for a given mail server!

           :param mail_server: Defined outgoing mail server.
           :param recordset mails: Queued mails to be filtered
           :param optional: Indicate that the mail server is default
        """
        self.ensure_one()
        filtered_mails = self.env['mail.mail']
        if self.use_smtp_quota:
            avail_quota = self._handle_smtp_quota(default=default)
            for mail in mails.sorted(key=lambda r: r.date):
                no_recipients = len(mail.send_get_email_list())
                if avail_quota - no_recipients >= 0:
                    filtered_mails |= mail
                    avail_quota -= no_recipients
                else:
                    break
        else:
            filtered_mails |= mails

        return filtered_mails
