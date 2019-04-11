# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class MailMessage(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(selection_add=[('sms', 'SMS')])
    sms_ids = fields.One2many('sms.sms', 'message_id')

    @api.multi
    def _get_message_format_fields(self):
        """ Override in order to fetch the field sms_ids """
        res = super(MailMessage, self)._get_message_format_fields()
        res.append('sms_ids')
        return res

    @api.multi
    def message_fetch_failed(self):
        """ Override in order to fetch the SMS failed """
        res = super(MailMessage, self).message_fetch_failed()
        return res + self.sms_ids._fetch_failed_sms()

    @api.multi
    def message_format(self):
        """ Override in order to retrieves data about SMS (recipient name and
            SMS status)
        """
        message_values = super(MailMessage, self).message_format()
        for message in message_values:
            records = self.env['sms.sms'].browse(message['sms_ids'])
            message['sms_ids'] = [[
                record.id,
                record.name,
                record.state
            ] for record in records]
        return message_values
