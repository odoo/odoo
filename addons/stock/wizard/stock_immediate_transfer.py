# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockImmediateTransfer(models.TransientModel):
    _name = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    pick_id = fields.Many2one('stock.picking')

    @api.model
    def default_get(self, fields):
        res = super(StockImmediateTransfer, self).default_get(fields)
        if not res.get('pick_id') and self._context.get('active_id'):
            res['pick_id'] = self._context['active_id']
        return res

    @api.multi
    def process(self):
        self.ensure_one()
        # If still in draft => confirm and assign
        if self.pick_id.state == 'draft':
            self.pick_id.action_confirm()
            if self.pick_id.state != 'assigned':
                self.pick_id.action_assign()
                if self.pick_id.state != 'assigned':
                    raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
        for move in self.pick_id.move_lines:
            if move.move_line_ids:
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            else:
                move.quantity_done = move.product_uom_qty
        self.pick_id.do_transfer()
