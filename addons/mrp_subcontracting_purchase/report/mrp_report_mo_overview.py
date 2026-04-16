# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_production(self, production_id):
        production = self.env['mrp.production'].browse(production_id)
        if production.subcontractor_id:
            subcontract_move = production.reference_ids.move_ids.filtered(lambda m: m.is_subcontract and m.product_id == production.product_id and m.partner_id == production.subcontractor_id)
            subcontracting_location = subcontract_move.picking_id.partner_id.with_company(subcontract_move.company_id).property_stock_subcontractor
            resupply_moves = production.move_raw_ids.move_orig_ids
            resupply_warehouse = resupply_moves.warehouse_id or subcontract_move.warehouse_id
            resupply_picking = resupply_moves.picking_id
            documents = [(resupply_picking._name, resupply_picking.id)]
            return production.with_context(
                search_warehouse=resupply_warehouse.id,
                search_location=[subcontracting_location.id, resupply_warehouse.lot_stock_id.id],
                po_line=subcontract_move.purchase_line_id,
                documents=documents)
        return super()._get_production(production_id)

    def _get_report_data(self, production_id):
        result = super()._get_report_data(production_id)
        production = self._get_production(production_id)
        if production.subcontractor_id:
            # subcontracted manufacturing order, the component lines exists
            # : add a purchase order line
            summary = result['summary']
            po_line = production.env.context.get('po_line')
            po = po_line.order_id
            quantity = production.product_uom_qty
            currency = summary['currency']
            price = po_line.tax_ids.compute_all(
                po_line.price_unit,
                currency=po.currency_id,
                quantity=production.uom_id._compute_quantity(quantity, po_line.uom_id),
                product=po_line.product_id,
                partner=po.partner_id,
                rounding_method='round_globally',
            )['total_void']
            price = po_line.currency_id._convert(price, currency, (po.company_id or self.env.company), fields.Date.today())
            seller_price = po_line.product_id._select_seller(quantity=quantity, uom_id=po_line.uom_id, params={'subcontractor_ids': production.bom_id.subcontractor_ids}).price
            replenishment = {
                'level': 1,
                'index': 'R',
                'model': 'purchase.order',
                'id': po.id,
                'name': po.name,
                'state': po.state,
                'formatted_state': self._format_state(po),
                'quantity': quantity,
                'uom_name': production.uom_id.display_name,
                'unit_cost': currency.round(price / quantity),
                'mo_cost': currency.round(price),
                'bom_cost': summary['currency'].round(quantity * seller_price),
                'currency': currency,
                'receipt': self._format_receipt_date('expected', po_line.date_planned),
            }
            replenishment['mo_cost_decorator'] = self._get_comparison_decorator(replenishment['bom_cost'], replenishment['mo_cost'], 0.01)
            result['replenishment'] = {'summary': replenishment}
            summary['unit_cost'] += replenishment.get('unit_cost', 0.0)
            summary['mo_cost'] += replenishment.get('mo_cost', 0.0)
            summary['bom_cost'] += replenishment.get('bom_cost', 0.0)
            summary['mo_cost_decorator'] = self._get_comparison_decorator(summary['bom_cost'], summary['mo_cost'], 0.01)
        return result

    def _get_replenishment_lines(self, production, warehouse, move_raw, replenish_data, level, current_index):
        res = super()._get_replenishment_lines(production, warehouse, move_raw, replenish_data, level, current_index)
        result = []
        for index, line in enumerate(res):
            result.append(line)
            summary = line['summary']
            product = move_raw.product_id
            quantity = summary['quantity']
            unit = move_raw.uom_id
            # check for subcontracted components at their different stages
            # - to order (no purchase order)
            # - draft purchase order
            # - confirmed purchase order (a subcontracted manufacturing order exists)
            if summary['model'] == 'to_order':
                bom = move_raw.product_id.bom_ids.filtered(lambda b: b.type == 'subcontract')[:1]
                if bom:
                    # subcontractable component not yet ordered: a line to replenish exists
                    # : add a line with the cost of components
                    result.append(self._make_components_line(summary, product, quantity, unit, bom, level, f"{current_index}-{index}"))
            elif summary['model'] == 'purchase.order':
                po = self.env[summary['model']].browse(summary['id'])
                move = po.order_line.move_ids.filtered(lambda m: m.product_id.id == product.id and m.is_subcontract)
                subcontracted_mo = move.move_orig_ids.production_id
                if subcontracted_mo:
                    # (at least) confirmed purchase order, a line with purchase order exists
                    # : add components hierarchy
                    subcontracted_mo = self._get_production(subcontracted_mo.id)
                    resupply_warehouse = self.env['stock.warehouse'].browse(production.env.context.get('search_warehouse'))
                    components = self._get_components_data(subcontracted_mo, resupply_warehouse, replenish_data=replenish_data, level=level + 1, current_index=current_index)
                    line['components'] = components
                    line['operations'] = {'details': [], 'summary': {'index': ''}}
                    line['byproducts'] = {'details': [], 'summary': {'index': ''}}
                    line['subcontracted'] = True
                else:
                    bom = self.env['mrp.bom']._bom_subcontract_find(product, subcontractor=po.partner_id)
                    if bom:
                        # draft purchase order, a line with the purchase order exists
                        # : add a line with the cost of components
                        result.append(self._make_components_line(summary, product, quantity, unit, bom, level, f"{current_index}-{index}"))
        return result

    def _make_components_line(self, summary, product, quantity, unit, bom, level, index):
        bom_price = product._compute_bom_price(bom)
        seller = product._select_seller(quantity=quantity, uom_id=unit, params={'subcontractor_ids': bom.subcontractor_ids})
        seller_price = seller.uom_id._compute_price(seller.price, product.uom_id)
        components_cost = unit._compute_quantity(quantity, product.uom_id) * (bom_price - seller_price)
        components_line = {'summary': {
            'level': level + 1,
            'index': f"{index}C",
            'name': _("Components"),
            'model': "components",
            'uom_precision': self._get_uom_precision(),
            'unit_cost': summary['currency'].round(components_cost / quantity),
            'mo_cost': summary['currency'].round(components_cost),
            'bom_cost': summary['currency'].round(components_cost),
            'currency': summary['currency'],
        }}
        summary['bom_cost'] = summary['currency'].round(quantity * seller_price)
        summary['mo_cost_decorator'] = self._get_comparison_decorator(summary['bom_cost'], summary['mo_cost'], 0.01)
        summary['subcontracted'] = True
        return components_line

    def _get_warehouse_locations(self, production, warehouse, replenish_data):
        if not replenish_data['warehouses'].get(warehouse.id):
            super()._get_warehouse_locations(production, warehouse, replenish_data)
            if 'search_location' in production.env.context:
                replenish_data['warehouses'][warehouse.id] = list(set(replenish_data['warehouses'][warehouse.id]) | set(production.env.context.get('search_location')))
        return replenish_data['warehouses'][warehouse.id]

    def _get_component_bom_cost(self, move_raw, quantity, doc_in=False):
        if doc_in and doc_in._name == 'purchase.order' and doc_in.mrp_production_count:
            productions = doc_in._get_mrp_productions().filtered(lambda p: p.product_id == move_raw.product_id)
            bom = productions.bom_id.filtered(lambda b: b.type == 'subcontract' and doc_in.partner_id in b.subcontractor_ids)
            if bom:
                seller_price = move_raw.product_id._select_seller(quantity=quantity, uom_id=move_raw.uom_id, params={'subcontractor_ids': doc_in.partner_id}).price
                return seller_price * quantity
        return super()._get_component_bom_cost(move_raw, quantity)

    def _compute_cost_sums(self, components, operations=False):
        total_mo_cost, total_bom_cost, total_real_cost = super()._compute_cost_sums(components, operations)
        if components and components[0].get('subcontracted'):
            for component in components[0]['components']:
                total_mo_cost += component.get('summary', {}).get('mo_cost', 0.0)
                total_bom_cost += component.get('summary', {}).get('bom_cost', 0.0)
                total_real_cost += component.get('summary', {}).get('real_cost', 0.0)
        return total_mo_cost, total_bom_cost, total_real_cost
