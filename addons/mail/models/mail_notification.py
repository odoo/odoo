# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.translate import _


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
            'res_partner_id': [notif.res_partner_id.id, notif.res_partner_id.display_name] if notif.res_partner_id else False,
        } for notif in self]
