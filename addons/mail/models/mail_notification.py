# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.translate import _


class Notification(models.Model):
    _name = 'mail.notification'
    _table = 'mail_message_res_partner_needaction_rel'
    _rec_name = 'res_partner_id'
    _log_access = False
    _description = 'Message Notifications'

    mail_message_id = fields.Many2one(
        'mail.message', 'Message', index=True, ondelete='cascade', required=True)
    res_partner_id = fields.Many2one(
        'res.partner', 'Needaction Recipient', index=True, ondelete='cascade', required=False)
    is_read = fields.Boolean('Is Read', index=True)
    notification_type = fields.Selection([
        ('inbox', 'Inbox'), ('email', 'Email')], string='Notification Type',
        default='inbox', index=True, required=True)
    notification_status = fields.Selection([
        ('ready', 'Ready to Send'),
        ('sent', 'Sent'),
        ('bounce', 'Bounced'),
        ('exception', 'Exception'),
        ('canceled', 'Canceled')], 'Email Status',
        default='ready', index=True)
    mail_id = fields.Many2one('mail.mail', 'Mail', index=True)
    # it would be technically possible to find notification from mail without adding a mail_id field on notification,
    # comparing partner_ids and message_ids, but this will involve to search notifications one by one since we want to match
    # bot value. Working with set inclusion, we could have a notif matching message from mail 1 and partner from mail 2, we dont want that.
    # The solution would be to iterate over mail or to filter mail after search,... or add a mail_id field on notification to KISS
    failure_type = fields.Selection(selection=[
            ("SMTP", "Connection failed (outgoing mail server problem)"),
            ("RECIPIENT", "Invalid email address"),
            ("BOUNCE", "Email address rejected by destination"),
            ("UNKNOWN", "Unknown error"),
            ], string='Failure type')
    failure_reason = fields.Text('Failure reason', copy=False)
    read_date = fields.Datetime('Read Date', copy=False)

    _sql_constraints = [
        # email notification;: partner is required
        ('notification_partner_required',
            "CHECK(notification_type NOT IN ('email', 'inbox') OR res_partner_id IS NOT NULL)",
            'Customer is required for inbox / email notification'),
    ]

    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('mail_notification_res_partner_id_is_read_notification_status_mail_message_id',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX mail_notification_res_partner_id_is_read_notification_status_mail_message_id ON mail_message_res_partner_needaction_rel (res_partner_id, is_read, notification_status, mail_message_id)')

    def format_failure_reason(self):
        self.ensure_one()
        if self.failure_type != 'UNKNOWN':
            return dict(type(self).failure_type.selection).get(self.failure_type, _('No Error'))
        else:
            return _("Unknown error") + ": %s" % (self.failure_reason or '')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_read'):
                vals['read_date'] = fields.Datetime.now()
        return super(Notification, self).create(vals_list)

    def write(self, vals):
        if vals.get('is_read'):
            vals['read_date'] = fields.Datetime.now()
        return super(Notification, self).write(vals)

    @api.model
    def _gc_notifications(self, max_age_days=180):
        domain = [
            ('is_read', '=', True),
            ('read_date', '<', fields.Datetime.now() - relativedelta(days=max_age_days)),
            ('res_partner_id.partner_share', '=', False),
            ('notification_status', 'in', ('sent', 'canceled'))
        ]
        return self.search(domain).unlink()
