# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class BidLineQty(models.TransientModel):
    _name = "bid.line.qty"
    _description = "Change Bid line quantity"

    qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)

    @api.multi
    def change_qty(self):
        self.ensure_one()
        if self.env.context.get('active_model') == 'purchase.order.line':
            self.env['purchase.order.line'].browse(self.env.context.get('active_ids')).write({'quantity_tendered': self.qty})
        return {'type': 'ir.actions.act_window_close'}
