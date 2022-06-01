# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.translate import _


class MailNotification(models.Model):
    _name = 'mail.notification'
    _table = 'mail_notification'
    _rec_name = 'res_partner_id'
    _log_access = False
    _description = 'Message Notifications'

    # origin
    author_id = fields.Many2one('res.partner', 'Author', ondelete='set null')
    mail_message_id = fields.Many2one('mail.message', 'Message', index=True, ondelete='cascade', required=True)
    mail_mail_id = fields.Many2one('mail.mail', 'Mail', index=True, help='Optional mail_mail ID. Used mainly to optimize searches.')
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
        # generic
        ("unknown", "Unknown error"),
        # mail
        ("mail_email_invalid", "Invalid email address"),
        ("mail_email_missing", "Missing email address"),
        ("mail_smtp", "Connection failed (outgoing mail server problem)"),
        ], string='Failure type')
    failure_reason = fields.Text('Failure reason', copy=False)

    _sql_constraints = [
        # email notification: partner is required
        ('notification_partner_required',
         "CHECK(notification_type NOT IN ('email', 'inbox') OR res_partner_id IS NOT NULL)",
         'Customer is required for inbox / email notification'),
    ]

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def init(self):
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS mail_notification_res_partner_id_is_read_notification_status_mail_message_id
                                    ON mail_notification (res_partner_id, is_read, notification_status, mail_message_id);
            CREATE INDEX IF NOT EXISTS mail_notification_author_id_notification_status_failure
                                    ON mail_notification (author_id, notification_status)
                                 WHERE notification_status IN ('bounce', 'exception');
        """)
        self.env.cr.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS unique_mail_message_id_res_partner_id_if_set
                                              ON %s (mail_message_id, res_partner_id)
                                           WHERE res_partner_id IS NOT NULL""" % self._table
        )

    @api.model_create_multi
    def create(self, vals_list):
        messages = self.env['mail.message'].browse(vals['mail_message_id'] for vals in vals_list)
        messages.check_access_rights('read')
        messages.check_access_rule('read')
        for vals in vals_list:
            if vals.get('is_read'):
                vals['read_date'] = fields.Datetime.now()
        return super(MailNotification, self).create(vals_list)

    def write(self, vals):
        if ('mail_message_id' in vals or 'res_partner_id' in vals) and not self.env.is_admin():
            raise AccessError(_("Can not update the message or recipient of a notification."))
        if vals.get('is_read'):
            vals['read_date'] = fields.Datetime.now()
        return super(MailNotification, self).write(vals)

    @api.model
    def _gc_notifications(self, max_age_days=180):
        domain = [
            ('is_read', '=', True),
            ('read_date', '<', fields.Datetime.now() - relativedelta(days=max_age_days)),
            ('res_partner_id.partner_share', '=', False),
            ('notification_status', 'in', ('sent', 'canceled'))
        ]
        return self.search(domain).unlink()

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def format_failure_reason(self):
        self.ensure_one()
        if self.failure_type != 'unknown':
            return dict(type(self).failure_type.selection).get(self.failure_type, _('No Error'))
        else:
            return _("Unknown error") + ": %s" % (self.failure_reason or '')

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def _filtered_for_web_client(self):
        """Returns only the notifications to show on the web client."""
        def _filter_unimportant_notifications(notif):
            if notif.notification_status in ['bounce', 'exception', 'canceled'] \
                    or notif.res_partner_id.partner_share:
                return True
            subtype = notif.mail_message_id.subtype_id
            return not subtype or subtype.track_recipients

        return self.filtered(_filter_unimportant_notifications)

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
