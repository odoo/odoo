# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _candidate_sort_key(self):
        self.ensure_one()
        res = super()._candidate_sort_key()
        if self.product_id in self.env.context.get('product_unbuild_map', ()):
            unbuild = self.env.context['product_unbuild_map'][self.product_id]
            # Give priority to the SVL that produced `self.product_id`
            res += (self.stock_move_id.id not in unbuild.mo_id.move_finished_ids.ids,)
        return res
