# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResendSms(models.TransientModel):
    _name = 'sms.resend'
    _description = 'Update mobile number and resend'

    partner_id = fields.Many2one('res.partner')
    partner_name = fields.Char(readonly=True)

    sms_id = fields.Many2one('sms.sms')
    number = fields.Char(required=True)

    @api.model
    def default_get(self, fields):
        rec = super(ResendSms, self).default_get(fields)
        sms_id = self.env['sms.sms'].browse(self.env.context.get('sms_id'))
        rec.update({
            'partner_id': sms_id.partner_id.id if sms_id.partner_id else False,
            'partner_name': sms_id.partner_id.name if sms_id.partner_id else False,
            'sms_id': sms_id.id,
            'number': sms_id.number,
        })
        return rec

    @api.multi
    def update_number_cancel(self):
        self.sms_id.cancel_sms()

    @api.multi
    def update_number_save(self):
        if self.partner_id:
            self.partner_id.write({'mobile': self.number})
        self.sms_id.write({'number': self.number})
        self.sms_id.send_sms()
