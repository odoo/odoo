# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()

    def _compute_kit_quantities(self, product_id, kit_qty, kit_bom, filters):
        if self.env.context.get("override_kit_filters"):
            filters['incoming_moves'] = lambda m: (
                (m.location_id.usage == 'supplier' or
                (m.location_id.usage == 'internal' and m.is_subcontract))
                and not m.origin_returned_move_id
                or (m.origin_returned_move_id and m.to_refund)
            )

        # Proceed with the updated filters
        return super()._compute_kit_quantities(product_id, kit_qty, kit_bom, filters)
