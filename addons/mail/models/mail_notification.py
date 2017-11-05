# -*- coding: utf-8 -*-

from odoo import api, fields, models


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
        ('exception', 'Exception')], 'Email Status',
        default='ready', index=True)

    @api.model_cr
    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('mail_notification_res_partner_id_is_read_email_status_mail_message_id',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX mail_notification_res_partner_id_is_read_email_status_mail_message_id ON mail_message_res_partner_needaction_rel (res_partner_id, is_read, email_status, mail_message_id)')
