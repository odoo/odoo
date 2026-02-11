# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_landed_cost(self, at_date=None):
        lcs = super()._get_landed_cost()
        if self.production_id.subcontractor_id:
            receipt_move = self.move_dest_ids
            lcs[self] |= super(StockMove, receipt_move)._get_landed_cost()[receipt_move]
        return lcs
