# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_warehouse(self, subcontract_move):
        if subcontract_move.sale_line_id:
            return subcontract_move.sale_line_id.order_id.warehouse_id
        return super(StockPicking, self)._get_warehouse(subcontract_move)

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        finished_moves = self.env['stock.move']
        for picking in self:
            done_productions = picking._get_subcontracted_productions().filtered(lambda p: p.state == 'done')
            for move in done_productions.move_finished_ids:
                finished_moves |= move
        if finished_moves:
            finished_moves.move_dest_ids.move_dest_ids._action_assign()
        return res
