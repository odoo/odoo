# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessError
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
        'res.partner', 'Needaction Recipient', index=True, ondelete='cascade', required=True)
    is_read = fields.Boolean('Is Read', index=True)
    is_email = fields.Boolean('Sent by Email', index=True)
    email_status = fields.Selection([
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

    @api.model_cr
    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('mail_notification_res_partner_id_is_read_email_status_mail_message_id',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX mail_notification_res_partner_id_is_read_email_status_mail_message_id ON mail_message_res_partner_needaction_rel (res_partner_id, is_read, email_status, mail_message_id)')

    @api.model
    def create(self, vals):
        msg = self.env['mail.message'].browse(vals['mail_message_id'])
        msg.check_access_rights('read')
        msg.check_access_rule('read')
        return super(Notification, self).create(vals)

    @api.multi
    def write(self, vals):
        if ('mail_message_id' in vals or 'res_partner_id' in vals) and not self.env.user._is_admin():
            raise AccessError(_("Can not update the message or recipient of a notification."))
        return super(Notification, self).write(vals)

    @api.multi
    def format_failure_reason(self):
        self.ensure_one()
        if self.failure_type != 'UNKNOWN':
            return dict(type(self).failure_type.selection).get(self.failure_type, _('No Error'))
        else:
            return _("Unknown error") + ": %s" % (self.failure_reason or '')
