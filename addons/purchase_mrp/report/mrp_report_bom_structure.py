# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportMrpReport_Bom_Structure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _format_route_info(self, rules, rules_delay, warehouse, product, bom, quantity):
        res = super()._format_route_info(rules, rules_delay, warehouse, product, bom, quantity)
        if self._is_buy_route(rules, product, bom):
            buy_rules = [rule for rule in rules if rule.action == 'buy']
            supplier = product._select_seller(quantity=quantity, uom_id=product.uom_id)
            if not supplier:
                # If no vendor found for the right quantity, we still want to display a vendor for the lead times
                supplier = product._select_seller(quantity=None, uom_id=product.uom_id)
            parent_bom = self.env.context.get('parent_bom')
            purchase_lead = parent_bom.company_id.days_to_purchase if parent_bom and parent_bom.company_id else 0
            if supplier:
                qty_supplier_uom = product.uom_id._compute_quantity(quantity, supplier.product_uom_id)
                return {
                    'route_type': 'buy',
                    'route_name': buy_rules[0].route_id.display_name,
                    'route_detail': supplier.with_context(use_simplified_supplier_name=True).display_name,
                    'lead_time': supplier.delay + rules_delay + purchase_lead,
                    'supplier_delay': supplier.delay + rules_delay + purchase_lead,
                    'supplier': supplier,
                    'route_alert': product.uom_id.compare(qty_supplier_uom, supplier.min_qty) < 0,
                    'qty_checked': quantity,
                }
        return res

    @api.model
    def _is_resupply_rules(self, rules, bom):
        return super()._is_resupply_rules(rules, bom) or any(rule.action == 'buy' for rule in rules)

    @api.model
    def _is_buy_route(self, rules, product, bom):
        return any(rule for rule in rules if rule.action == 'buy' and product.seller_ids)

    @api.model
    def _get_resupply_availability(self, route_info, components):
        if route_info.get('route_type') == 'buy':
            supplier_delay = route_info.get('supplier_delay', 0)
            return ('estimated', supplier_delay)
        return super()._get_resupply_availability(route_info, components)
