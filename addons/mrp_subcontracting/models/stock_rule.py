# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals["is_subcontract"] = False
        return new_move_vals


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    def _get_product_routes(self, product):
        route_ids = super()._get_product_routes(product)
        resupply_subcontractor_route = self.env.ref('mrp_subcontracting.route_resupply_subcontractor_mto', raise_if_not_found=False)
        has_subcontract_bom = any(bom_line.bom_id.type == 'subcontract' for bom_line in product.bom_line_ids)
        if resupply_subcontractor_route and has_subcontract_bom and product.product_tmpl_id.qty_available > 0:
            route_ids |= resupply_subcontractor_route
        return route_ids.sorted(lambda r: r.sequence)
