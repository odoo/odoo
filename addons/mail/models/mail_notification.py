# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.constants import GC_UNLINK_LIMIT
from odoo.tools.translate import _
from odoo.addons.mail.tools.discuss import Store


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
    # set if no matching partner exists (mass mail)
    # must be normalized except if notification is cancel/failure from invalid email
    mail_email_address = fields.Char(help='Recipient email address')
    # status
    notification_type = fields.Selection([
        ('inbox', 'Inbox'), ('email', 'Email')
        ], string='Notification Type', default='inbox', index=True, required=True)
    notification_status = fields.Selection([
        ('ready', 'Ready to Send'),
        ('process', 'Processing'),  # being checked by intermediary like IAP for sms
        ('pending', 'Sent'),  # used with SMS; mail does not differentiate sent from delivered
        ('sent', 'Delivered'),
        ('bounce', 'Bounced'),
        ('exception', 'Exception'),
        ('canceled', 'Cancelled')
        ], string='Status', default='ready', index=True)
    is_read = fields.Boolean('Is Read', index=True)
    read_date = fields.Datetime('Read Date', copy=False)
    failure_type = fields.Selection(selection=[
        # generic
        ("unknown", "Unknown error"),
        # mail
        ("mail_bounce", "Bounce"),
        ("mail_email_invalid", "Invalid email address"),
        ("mail_email_missing", "Missing email address"),
        ("mail_from_invalid", "Invalid from address"),
        ("mail_from_missing", "Missing from address"),
        ("mail_smtp", "Connection failed (outgoing mail server problem)"),
        # mass mode
        ("mail_bl", "Blacklisted Address"),
        ("mail_optout", "Opted Out"),
        ("mail_dup", "Duplicated Email")], string='Failure type')
    failure_reason = fields.Text('Failure reason', copy=False)

    _notification_partner_required = models.Constraint(
        "CHECK(notification_type != 'inbox' OR res_partner_id IS NOT NULL)",
        'Customer is required for inbox notification',
    )
    _notification_partner_or_email_required = models.Constraint(
        "CHECK(notification_type != 'email' OR failure_type IS NOT NULL OR res_partner_id IS NOT NULL OR COALESCE(mail_email_address, '') != '')",
        'Customer or email is required for inbox / email notification',
    )
    _res_partner_id_is_read_notification_status_mail_message_id = models.Index("(res_partner_id, is_read, notification_status, mail_message_id)")
    _author_id_notification_status_failure = models.Index("(author_id, notification_status) WHERE notification_status IN ('bounce', 'exception')")
    _unique_mail_message_id_res_partner_id_ = models.UniqueIndex("(mail_message_id, res_partner_id) WHERE res_partner_id IS NOT NULL")

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        messages = self.env['mail.message'].browse(vals['mail_message_id'] for vals in vals_list)
        messages.check_access('read')
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
        records = self.search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT  # done, remaining

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def format_failure_reason(self):
        self.ensure_one()
        if self.failure_type != 'unknown':
            return dict(self._fields['failure_type'].selection).get(self.failure_type, _('No Error'))
        else:
            if self.failure_reason:
                return _("Unknown error: %(error)s", error=self.failure_reason)
            return _("Unknown error")

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def _filtered_for_web_client(self):
        """Returns only the notifications to show on the web client."""
        def _filter_unimportant_notifications(notif):
            if notif.notification_status in ['bounce', 'exception', 'canceled'] \
                    or notif.res_partner_id.partner_share or notif.mail_email_address:
                return True
            subtype = notif.mail_message_id.subtype_id
            return not subtype or subtype.track_recipients

        return self.filtered(_filter_unimportant_notifications)

    def _to_store_defaults(self, target):
        return [
            "mail_email_address",
            "failure_type",
            "mail_message_id",
            "notification_status",
            "notification_type",
            Store.One("res_partner_id", ["name", "email"]),
        ]
