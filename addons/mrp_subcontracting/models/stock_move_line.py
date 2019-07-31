# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self, values):
        move_lines_subcontracted = self.filtered(lambda ml: ml.move_id.is_subcontract)
        if not move_lines_subcontracted:
            return super(StockMoveLine, self).write(values)
        for ml in move_lines_subcontracted:
            candidates = ml.move_id.move_orig_ids.move_line_ids
            candidate = candidates.filtered(lambda c:
                c.qty_done == ml.qty_done and ml.product_uom_qty == c.product_uom_qty and
                ml.product_uom_id == c.product_uom_id and c.lot_id == ml.lot_id)
            candidate = candidate and candidate[0] or self.env['stock.move.line']
            candidate.write(values)
        return super(StockMoveLine, self).write(values)
