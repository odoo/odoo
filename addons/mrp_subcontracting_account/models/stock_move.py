# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self, exclude_external_cost=False, **kwargs):
        price_unit = super()._get_price_unit(exclude_external_cost=exclude_external_cost, **kwargs)
        if not exclude_external_cost:
            return price_unit
        moves = self.filtered(
            lambda m: m.production_id
            and m.move_dest_ids.filtered(lambda d: d.state == "done")[-1:].is_subcontract
            and m.product_id.cost_method != "standard"
        )
        if not moves:
            return price_unit
        total_qty = sum(m._get_valued_qty(signed=True) for m in self)
        if not total_qty:
            return price_unit
        extra_value = sum(
            m.production_id.extra_cost * m.uom_id._compute_quantity(m.quantity, m.product_id.uom_id)
            for m in moves
        )
        return price_unit - extra_value / total_qty
