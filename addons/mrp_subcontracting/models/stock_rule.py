# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals["is_subcontract"] = False
        return new_move_vals

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        if not move_values.get('partner_id'):
            if values.get('move_dest_ids') and values['move_dest_ids'].raw_material_production_id.subcontractor_id:
                move_values['partner_id'] = values['move_dest_ids'].raw_material_production_id.subcontractor_id.id
        return move_values

    def _filter_warehouse_routes(self, product, warehouses, route):
        if any(rule.action == 'pull' and rule.picking_type_id.code == 'internal' and rule.location_src_id.is_subcontract() for rule in route.rule_ids):
            if any(bom_line.bom_id.type == 'subcontract' for bom_line in product.bom_line_ids):
                return super()._filter_warehouse_routes(product, warehouses, route)
            return False
        return super()._filter_warehouse_routes(product, warehouses, route)
