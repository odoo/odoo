# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from operator import itemgetter

from odoo import exceptions, fields, models
from odoo.tools import groupby


class MailMessage(models.Model):
    """ Override MailMessage class in order to add a new type: SMS messages.
    Those messages comes with their own notification method, using SMS
    gateway. """
    _inherit = 'mail.message'

    message_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': lambda recs: recs.write({'message_type': 'email'})})
    has_sms_error = fields.Boolean(
        'Has SMS error', compute='_compute_has_sms_error', search='_search_has_sms_error',
        help='Has error')

    def _compute_has_sms_error(self):
        sms_error_from_notification = self.env['mail.notification'].sudo().search([
            ('notification_type', '=', 'sms'),
            ('mail_message_id', 'in', self.ids),
            ('notification_status', '=', 'exception')]).mapped('mail_message_id')
        for message in self:
            message.has_sms_error = message in sms_error_from_notification

    def _search_has_sms_error(self, operator, operand):
        if operator == '=' and operand:
            return ['&', ('notification_ids.notification_status', '=', 'exception'), ('notification_ids.notification_type', '=', 'sms')]
        raise NotImplementedError()

    def message_format(self, format_reply=True):
        """ Override in order to retrieves data about SMS (recipient name and
            SMS status)

        TDE FIXME: clean the overall message_format thingy
        """
        message_values = super(MailMessage, self).message_format(format_reply=format_reply)
        all_sms_notifications = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', [r['id'] for r in message_values]),
            ('notification_type', '=', 'sms')
        ])
        msgid_to_notif = defaultdict(lambda: self.env['mail.notification'].sudo())
        for notif in all_sms_notifications:
            msgid_to_notif[notif.mail_message_id.id] += notif

        for message in message_values:
            customer_sms_data = [(notif.id, notif.res_partner_id.display_name or notif.sms_number, notif.notification_status) for notif in msgid_to_notif.get(message['id'], [])]
            message['sms_ids'] = customer_sms_data
        return message_values
