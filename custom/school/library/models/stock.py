# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo import workflow


class StockMove(models.Model):
    _inherit = 'stock.move'

    customer_ref = fields.Char('Customer reference')
    origin_ref = fields.Char('Origin')

    @api.multi
    def action_cancel(self):
        if not len(self.ids):
            return True
        pickings = {}
        for move in self:
            if move.state in ('confirmed', 'waiting', 'assigned', 'draft'):
                if move.picking_id:
                    pickings[move.picking_id.id] = True
        self.write({'state': 'cancel'})
        for pick_id in pickings:
            workflow.trg_validate(self._uid, 'stock.picking', pick_id,
                                  'button_cancel', self._cr)
        ids2 = []
        for res in self.read(['move_dest_id']):
            if res['move_dest_id']:
                ids2.append(res['move_dest_id'][0])
#        for stock_id in self.ids:
            self.trg_trigger()
        return True


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _order = "create_date desc"

    sale_id = fields.Many2one('sale.order', 'Sale Order', ondelete='set null',
                              readonly=True, default=False)
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order',
                                  ondelete='set null', readonly=True,
                                  default=False)
    date_done = fields.Datetime('Picking date', readonly=True)
