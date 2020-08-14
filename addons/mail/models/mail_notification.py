# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.tools.translate import _
from datetime import timedelta


class MailNotification(models.Model):
    _name = 'mail.notification'
    _table = 'mail_message_res_partner_needaction_rel'
    _rec_name = 'res_partner_id'
    _log_access = False
    _description = 'Message Notifications'

    # origin
    mail_message_id = fields.Many2one('mail.message', 'Message', index=True, ondelete='cascade', required=True)
    mail_id = fields.Many2one('mail.mail', 'Mail', index=True, help='Optional mail_mail ID. Used mainly to optimize searches.')
    # recipient
    res_partner_id = fields.Many2one('res.partner', 'Recipient', index=True, ondelete='cascade')
    # status
    notification_type = fields.Selection([
        ('inbox', 'Inbox'), ('email', 'Email')
        ], string='Notification Type', default='inbox', index=True, required=True)
    notification_status = fields.Selection([
        ('ready', 'Ready to Send'),
        ('sent', 'Sent'),
        ('bounce', 'Bounced'),
        ('exception', 'Exception'),
        ('canceled', 'Canceled')
        ], string='Status', default='ready', index=True)
    is_read = fields.Boolean('Is Read', index=True)
    read_date = fields.Datetime('Read Date', copy=False)
    failure_type = fields.Selection(selection=[
        ("SMTP", "Connection failed (outgoing mail server problem)"),
        ("RECIPIENT", "Invalid email address"),
        ("BOUNCE", "Email address rejected by destination"),
        ("UNKNOWN", "Unknown error"),
        ], string='Failure type')
    failure_reason = fields.Text('Failure reason', copy=False)

    _sql_constraints = [
        # email notification;: partner is required
        ('notification_partner_required',
         "CHECK(notification_type NOT IN ('email', 'inbox') OR res_partner_id IS NOT NULL)",
         'Customer is required for inbox / email notification'),
    ]

    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s',
                         ('mail_notification_res_partner_id_is_read_notification_status_mail_message_id',))
        if not self._cr.fetchone():
            self._cr.execute("""
                CREATE INDEX mail_notification_res_partner_id_is_read_notification_status_mail_message_id
                          ON mail_message_res_partner_needaction_rel (res_partner_id, is_read, notification_status, mail_message_id)
            """)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_read'):
                vals['read_date'] = fields.Datetime.now()
        return super(MailNotification, self).create(vals_list)

    def write(self, vals):
        if vals.get('is_read'):
            vals['read_date'] = fields.Datetime.now()
        return super(MailNotification, self).write(vals)

    def format_failure_reason(self):
        self.ensure_one()
        if self.failure_type != 'UNKNOWN':
            return dict(type(self).failure_type.selection).get(self.failure_type, _('No Error'))
        else:
            return _("Unknown error") + ": %s" % (self.failure_reason or '')

    @api.model
    def _gc_notifications(self, max_age_days=180):
        domain = [
            ('is_read', '=', True),
            ('read_date', '<', fields.Datetime.now() - relativedelta(days=max_age_days)),
            ('res_partner_id.partner_share', '=', False),
            ('notification_status', 'in', ('sent', 'canceled'))
        ]
        return self.search(domain).unlink()

    def _filtered_for_web_client(self):
        """Returns only the notifications to show on the web client."""
        return self.filtered(lambda n:
            n.notification_type != 'inbox' and
            (n.notification_status in ['bounce', 'exception', 'canceled'] or n.res_partner_id.partner_share)
        )

    def _notification_format(self):
        """Returns the current notifications in the format expected by the web
        client."""
        return [{
            'id': notif.id,
            'notification_type': notif.notification_type,
            'notification_status': notif.notification_status,
            'failure_type': notif.failure_type,
            'partner_id': [notif.res_partner_id.id, notif.res_partner_id.display_name],
        } for notif in self]

    @api.model
    def _cron_notify_admins(self):
        """
            Cron activity : Posts notifications about failed mails/sms and other batch failures...
            This cron was created to avoid adding notification code (failure counter, '_notify_admins()' method...) while mail stack processed.
        """
        cron = self.env.ref('mail.ir_cron_mail_notify_administrators')
        # Get the last check date (related to the cron period == 1 day)
        previous_date = fields.Datetime.now() - relativedelta(**{cron.interval_type: cron.interval_number})

        # Count failed mails : (we can get failed mails from 'mail.mail')
        # Some emails (ex : for ignored recipients) are deleted from mails list, so we get them from 'mail.notification'
        failed_ignored_emails_counter = self.env['mail.notification'].sudo().search_count([
            # We use 'mail_message_id.create_date' as a substitute for date or create_date in 'mail.notification'
            ('mail_message_id.create_date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
            ('notification_status', '=', 'exception'),
            ('notification_type', '=', 'email'),
            ('failure_type', '=', 'RECIPIENT')]
        )
        # The 'mail.notification' counter will count only 'RECIPIENT' related failures.
        failed_emails_counter = self.env['mail.mail'].sudo().search_count([
                ('date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                ('state', '=', 'exception')])

        # Get notifications w-action (used to add a link to sms-mail notifs in admins channel)
        mail_sms_notifications_window_action = self.env.ref('mail.mail_notification_action').id

        # '_notify_admins' methods in daily cron job should use a repeat_delay of 1 day
        if failed_emails_counter:
            self._notify_admins(
                *self._get_admin_notification('mail__smtp_connection')(
                    failed_emails_counter,
                    mail_sms_notifications_window_action
                ),
                repeat_delay=timedelta(days=1)
            )
        if failed_ignored_emails_counter:
            self._notify_admins(
                *self._get_admin_notification('mail__invalid_recipient')(
                    failed_ignored_emails_counter,
                    mail_sms_notifications_window_action
                ),
                repeat_delay=timedelta(days=1)
            )
