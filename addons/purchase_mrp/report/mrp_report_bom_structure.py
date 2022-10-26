# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _format_route_info(self, rules, rules_delay, warehouse, product, bom, quantity):
        res = super()._format_route_info(rules, rules_delay, warehouse, product, bom, quantity)
        if self._is_buy_route(rules, product, bom):
            buy_rules = [rule for rule in rules if rule.action == 'buy']
            supplier = product._select_seller(quantity=quantity, uom_id=product.uom_id)
            if supplier:
                return {
                    'route_type': 'buy',
                    'route_name': buy_rules[0].route_id.display_name,
                    'route_detail': supplier.display_name,
                    'lead_time': supplier.delay + rules_delay,
                    'supplier_delay': supplier.delay + rules_delay,
                    'supplier': supplier,
                }
        return res

    @api.model
    def _is_buy_route(self, rules, product, bom):
        return any(rule for rule in rules if rule.action == 'buy' and product.seller_ids)

    @api.model
    def _get_resupply_availability(self, route_info, components):
        if route_info.get('route_type') == 'buy':
            supplier_delay = route_info.get('supplier_delay', 0)
            return ('estimated', supplier_delay)
        return super()._get_resupply_availability(route_info, components)
