# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class SMSRecipient(models.TransientModel):
    _name = 'sms.sms.resend'
    _description = 'SMS resend object'

    sms_resend_wizard_id = fields.Many2one('sms.resend')
    sms_id = fields.Many2one('sms.sms')
    resend = fields.Boolean(string="Send Again", default=True)
    message = fields.Selection(related='sms_id.error_code')
    name = fields.Char()
    number = fields.Char()

class SMSResend(models.TransientModel):
    _name = 'sms.resend'
    _description = 'SMS resend wizard'

    mail_message_id = fields.Many2one('mail.message', 'Message', readonly=True)
    sms_resend_ids = fields.One2many('sms.sms.resend', 'sms_resend_wizard_id', string='Recipients')
    has_cancel = fields.Boolean(compute='_compute_has_cancel')
    has_insufficient_credit = fields.Boolean(compute='_compute_has_insufficient_credit') 

    @api.depends("sms_resend_ids")
    def _compute_has_insufficient_credit(self):
        self.has_insufficient_credit = self.sms_resend_ids.filtered(lambda p: p.message == 'insufficient_credit')

    @api.depends("sms_resend_ids")
    def _compute_has_cancel(self):
        self.has_cancel = self.sms_resend_ids.filtered(lambda p: not p.resend)

    @api.model
    def default_get(self, fields):
        result = super(SMSResend, self).default_get(fields)
        message_id = self._context.get('mail_message_to_resend')
        if message_id:
            mail_message_id = self.env['mail.message'].browse(message_id)
            sms_ids = mail_message_id.sms_ids.filtered(lambda sms: sms.state == 'error')
            sms_resend_ids = [(0, 0, {
                    'sms_id': sms.id,
                    'resend': True,
                    'name': sms.name,
                    'number': sms.number,
                    'message': sms.error_code
                }) for sms in sms_ids]
            result.update({
                'mail_message_id': mail_message_id.id,
                'sms_resend_ids': sms_resend_ids,
            })
        else:
            raise UserError('No message_id found in context')
        return result

    @api.multi
    def resend_sms_action(self):
        self.ensure_one()
        to_resend = self.sms_resend_ids.filtered(lambda sms: sms.resend)
        for sms in to_resend:
            sms.sms_id.number = sms.number
            sms.sms_id._send()
        to_cancel = self.sms_resend_ids.filtered(lambda sms: not sms.resend)
        for sms in to_cancel:
            sms.sms_id.state = 'canceled'
        self.sms_resend_ids.mapped('sms_id')._notify_sms_update()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def ignore_sms_action(self):
        self.ensure_one()
        for sms in self.sms_resend_ids:
            sms.sms_id.state = 'canceled'
        self.sms_resend_ids.mapped('sms_id')._notify_sms_update()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def cancel_sms_action(self):
        self.ensure_one()
        for sms in self.sms_resend_ids:
            sms.sms_id.state = 'canceled'
        self.sms_resend_ids.mapped('sms_id')._notify_sms_update()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def buy_credits(self):
        url = self.env['iap.account'].get_credits_url(service_name='sms')
        return {
            'type': 'ir.actions.act_url',
            'url': url,
        }
