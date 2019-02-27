# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Message(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(selection_add=[('sms', 'SMS')])

    sms_error = fields.Boolean('Error', compute='_compute_sms_error')
    sms_status = fields.Char('Status', compute='_compute_sms_error')

    sms_ids = fields.One2many('sms.sms', 'message_id', 'SMS')

    @api.multi
    def _get_message_format_fields(self):
        res = super(Message, self)._get_message_format_fields()
        res.append('sms_error')
        res.append('sms_status')
        return res

    @api.multi
    @api.depends('sms_ids', 'sms_ids.state')
    def _compute_sms_error(self):
        for message in self:
            if message.message_type == 'sms' and message.sms_ids:
                message.sms_error = message.sms_ids[0].state == 'error'
                message.sms_status = message.sms_ids[0].error_code if message.sms_ids[0].state == 'error' else message.sms_ids[0].state
            else:
                message.sms_error = False
                message.sms_status = ''

    @api.multi
    def cancel_sms(self):
        self.mapped('sms_ids').cancel_sms()

    @api.multi
    def send_sms(self):
        self.mapped('sms_ids').send_sms()
