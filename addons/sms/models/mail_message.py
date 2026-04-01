# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailMessage(models.Model):
    """ Override MailMessage class in order to add a new type: SMS messages.
    Those messages comes with their own notification method, using SMS
    gateway. """
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('sms', 'SMS')],
        ondelete={'sms': lambda recs: recs.write({'message_type': 'comment'})})
    has_sms_error = fields.Boolean(
        'Has SMS error', compute='_compute_has_sms_error', search='_search_has_sms_error')

    def _compute_has_sms_error(self):
        sms_error_from_notification = self.env['mail.notification'].sudo().search([
            ('notification_type', '=', 'sms'),
            ('mail_message_id', 'in', self.ids),
            ('notification_status', '=', 'exception')]).mapped('mail_message_id')
        for message in self:
            message.has_sms_error = message in sms_error_from_notification

    def _search_has_sms_error(self, operator, operand):
        if operator != 'in':
            return NotImplemented
        return [('notification_ids', 'any', [
            ('notification_status', '=', 'exception'),
            ('notification_type', '=', 'sms'),
        ])]
