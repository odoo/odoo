# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ConfirmStockSms(models.TransientModel):
    _name = 'confirm.stock.sms'
    _description = 'Confirm Stock SMS'

    picking_id = fields.Many2one('stock.picking', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, related='picking_id.company_id')

    def send_sms(self):
        self.ensure_one()
        if not self.company_id.has_received_warning_stock_sms:
            self.company_id.sudo().write({'has_received_warning_stock_sms': True})
        return self.picking_id.button_validate()

    def dont_send_sms(self):
        self.ensure_one()
        if not self.company_id.has_received_warning_stock_sms:
            self.company_id.sudo().write({
                'has_received_warning_stock_sms': True,
                'stock_move_sms_validation': False,
            })
        return self.picking_id.button_validate()
