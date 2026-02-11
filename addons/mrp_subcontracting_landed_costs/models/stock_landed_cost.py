# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class StockValuationAdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    def _get_adjustment_line_move(self):
        moves = self.env['stock.move']
        for line in self: 
            subcontracted_productions = line.move_id._get_subcontract_production()
            if line.move_id.is_subcontract and subcontracted_productions and len(subcontracted_productions.move_finished_ids) == 1:
                moves |= subcontracted_productions.move_finished_ids
            else:
                moves |= super()._get_adjustment_line_move()
        return moves
