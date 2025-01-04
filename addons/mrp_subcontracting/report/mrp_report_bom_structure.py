# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields
from odoo.tools import float_compare


class ReportMrpReport_Bom_Structure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_subcontracting_line(self, bom, seller, level, bom_quantity):
        ratio_uom_seller = seller.product_uom_id.factor / bom.product_uom_id.factor
        price = seller.currency_id._convert(seller.price, self.env.company.currency_id, (bom.company_id or self.env.company), fields.Date.today())
        return {
            'name': seller.partner_id.display_name,
            'partner_id': seller.partner_id.id,
            'quantity': bom_quantity,
            'uom': bom.product_uom_id.name,
            'prod_cost': price / ratio_uom_seller * bom_quantity,
            'bom_cost': price / ratio_uom_seller * bom_quantity,
            'level': level or 0
        }

    def _get_bom_data(self, bom, warehouse, product=False, line_qty=False, bom_line=False, level=0, parent_bom=False, parent_product=False, index=0, product_info=False, ignore_stock=False, simulated_leaves_per_workcenter=False):
        res = super()._get_bom_data(bom, warehouse, product, line_qty, bom_line, level, parent_bom, parent_product, index, product_info, ignore_stock, simulated_leaves_per_workcenter)
        if bom.type == 'subcontract' and not self.env.context.get('minimized', False):
            if not res['product']:
                seller = bom.product_tmpl_id.seller_ids.filtered(lambda s: s.partner_id in bom.subcontractor_ids)[:1]
            else:
                seller = res['product']._select_seller(quantity=res['quantity'], uom_id=bom.product_uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            if seller:
                res['subcontracting'] = self._get_subcontracting_line(bom, seller, level + 1, res['quantity'])
                if not self.env.context.get('minimized', False):
                    res['bom_cost'] += res['subcontracting']['bom_cost']
        return res

    def _get_bom_array_lines(self, data, level, unfolded_ids, unfolded, parent_unfolded):
        lines = super()._get_bom_array_lines(data, level, unfolded_ids, unfolded, parent_unfolded)

        if data.get('subcontracting'):
            subcontract_info = data['subcontracting']
            lines.append({
                'name': _("Subcontracting: %s", subcontract_info['name']),
                'type': 'subcontract',
                'uom': False,
                'quantity': subcontract_info['quantity'],
                'bom_cost': subcontract_info['bom_cost'],
                'prod_cost': subcontract_info['prod_cost'],
                'level': subcontract_info['level'],
                'visible': level == 1 or unfolded or parent_unfolded
            })
        return lines

    @api.model
    def _need_special_rules(self, product_info, parent_bom=False, parent_product=False):
        if parent_bom and parent_product:
            parent_info = product_info.get(parent_product.id, {}).get(parent_bom.id, {})
            return parent_info and parent_info.get('route_type') == 'subcontract'
        return super()._need_special_rules(product_info, parent_bom, parent_product)

    @api.model
    def _find_special_rules(self, product, product_info, current_bom=False, parent_bom=False, parent_product=False):
        res = super()._find_special_rules(product, product_info, current_bom, parent_bom, parent_product)
        if not parent_bom or not parent_product:
            return res
        # If no rules could be found within the warehouse, check if the product is a component from a subcontracted product.
        parent_info = product_info.get(parent_product.id, {}).get(parent_bom.id, {})
        if parent_info and parent_info.get('route_type') == 'subcontract':
            # Since the product is subcontracted, check the subcontracted location for rules instead of the warehouse.
            subcontracting_loc = parent_info['supplier'].partner_id.property_stock_subcontractor
            found_rules = product._get_rules_from_location(subcontracting_loc)
            if found_rules and self._is_resupply_rules(found_rules, current_bom):
                # We only want to show the effective resupply (i.e. a form of manufacture or buy)
                return found_rules
        return res

    @api.model
    def _format_route_info(self, rules, rules_delay, warehouse, product, bom, quantity):
        res = super()._format_route_info(rules, rules_delay, warehouse, product, bom, quantity)
        subcontract_rules = [rule for rule in rules if rule.action == 'buy' and bom and bom.type == 'subcontract']
        if subcontract_rules:
            supplier = product._select_seller(quantity=quantity, uom_id=product.uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            if not supplier:
                # If no vendor found for the right quantity, we still want to display a vendor for the lead times
                supplier = product._select_seller(quantity=None, uom_id=product.uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            # for subcontracting, we can't decide the lead time without component's resupply availability
            # we only return necessary info and calculate the lead time late when we have component's data
            if supplier:
                qty_supplier_uom = product.uom_id._compute_quantity(quantity, supplier.product_uom_id)
                return {
                    'route_type': 'subcontract',
                    'route_name': subcontract_rules[0].route_id.display_name,
                    'route_detail': supplier.display_name,
                    'lead_time': rules_delay,
                    'supplier': supplier,
                    'route_alert': float_compare(qty_supplier_uom, supplier.min_qty, precision_rounding=product.uom_id.rounding) < 0,
                    'qty_checked': quantity,
                    'bom': bom,
                }

        return res

    @api.model
    def _get_quantities_info(self, product, bom_uom, product_info, parent_bom=False, parent_product=False):
        quantities_info = super()._get_quantities_info(product, bom_uom, product_info, parent_bom, parent_product)
        if parent_product and parent_bom and parent_bom.type == 'subcontract' and product.is_storable:
            route_info = product_info.get(parent_product.id, {}).get(parent_bom.id, {})
            if route_info and route_info['route_type'] == 'subcontract':
                subcontracting_loc = route_info['supplier'].partner_id.property_stock_subcontractor
                subloc_product = product.with_context(location=subcontracting_loc.id, warehouse_id=False)
                subloc_product.fetch(['free_qty', 'qty_available'])
                stock_loc = f"subcontract_{subcontracting_loc.id}"
                if not product_info[product.id]['consumptions'].get(stock_loc, False):
                    product_info[product.id]['consumptions'][stock_loc] = 0
                quantities_info['free_to_manufacture_qty'] = product.uom_id._compute_quantity(subloc_product.free_qty, bom_uom)
                quantities_info['free_qty'] = quantities_info['free_to_manufacture_qty']
                quantities_info['on_hand_qty'] = product.uom_id._compute_quantity(subloc_product.qty_available, bom_uom)
                quantities_info['stock_loc'] = stock_loc

        return quantities_info

    @api.model
    def _get_resupply_availability(self, route_info, components):
        resupply_state, resupply_delay = super()._get_resupply_availability(route_info, components)
        if route_info.get('route_type') == 'subcontract':
            max_component_delay = self._get_max_component_delay(components)
            if max_component_delay is False:
                return ('unavailable', False)
            # Calculate the lead time for subcontracting, keep same as `_get_lead_days`
            vendor_lead_time = route_info['supplier'].delay
            manufacture_lead_time = route_info['bom'].produce_delay
            subcontract_delay = resupply_delay if resupply_delay else 0
            subcontract_delay += max(vendor_lead_time, manufacture_lead_time) + max_component_delay
            route_info['manufacture_delay'] = route_info['lead_time'] + max(vendor_lead_time, manufacture_lead_time)
            route_info['lead_time'] += max(vendor_lead_time, manufacture_lead_time + route_info['bom'].days_to_prepare_mo)
            return ('estimated', subcontract_delay)
        return (resupply_state, resupply_delay)
