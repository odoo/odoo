# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('line_ids.quantity', 'stock_account_valuation_corrected_qty')
    def _compute_stock_account_qty(self):
        for record in self:
            rslt = 0.0
            for line in record.line_ids:
                if line.debit:
                    rslt += line.quantity
            record.stock_account_move_qty = rslt
            record.stock_account_needing_correction = record.stock_account_move_qty - record.stock_account_valuation_corrected_qty

    stock_account_valuation_correction = fields.Boolean(string="Is valuation correction move", default=False)
    stock_account_move_qty = fields.Integer(compute='_compute_stock_account_qty')
    stock_account_needing_correction = fields.Integer(compute='_compute_stock_account_qty')
    stock_account_valuation_corrected_qty = fields.Integer(default=0)
    #TODO OCO : intégrer ce champ dans le cas 2
