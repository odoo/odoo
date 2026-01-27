# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _contextualized_production(self, production):
        if production.subcontractor_id:
            resupply_moves = production.move_raw_ids.move_orig_ids
            resupply_warehouse = resupply_moves.warehouse_id
            resupply_picking = resupply_moves.picking_id
            documents = [(resupply_picking._name, resupply_picking.id)]
            return production.with_context(warehouse=resupply_warehouse, warehouse_id=resupply_warehouse.id, documents=documents)
        return super()._contextualized_production(production)

    def _get_report_data(self, production_id):
        result = super()._get_report_data(production_id)
        summary = result['summary']
        if summary['model'] == 'mrp.production':
            mo = self.env[summary['model']].browse(summary['id'])
            if mo.subcontractor_id:
                po_line = mo.move_finished_ids.move_dest_ids.purchase_line_id
                po = po_line.order_id
                quantity = mo.product_uom_qty
                currency = summary['currency']
                price = po_line.tax_ids.compute_all(
                    po_line.price_unit,
                    currency=po.currency_id,
                    quantity=mo.uom_id._compute_quantity(quantity, po_line.uom_id),
                    product=po_line.product_id,
                    partner=po.partner_id,
                    rounding_method='round_globally',
                )['total_void']
                price = po_line.currency_id._convert(price, currency, (po.company_id or self.env.company), fields.Date.today())
                seller_price = po_line.product_id._select_seller(quantity=quantity, uom_id=po_line.uom_id, params={'subcontractor_ids': mo.bom_id.subcontractor_ids}).price
                replenishment = {
                    'level': 1,
                    'index': 'R',
                    'model': 'purchase.order',
                    'id': po.id,
                    'name': po.name,
                    'state': po.state,
                    'formatted_state': self._format_state(po),
                    'quantity': quantity,
                    'unit_cost': currency.round(price / quantity),
                    'mo_cost': currency.round(price),
                    'bom_cost': summary['currency'].round(quantity * seller_price),
                    'currency_id': summary['currency_id'],
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

    def _get_replenishment_lines(self, production, move_raw, replenish_data, level, current_index):
        result = super()._get_replenishment_lines(production, move_raw, replenish_data, level, current_index)
        if len(result) == 1:
            summary = result[0]['summary']
            quantity = summary['quantity']
            product = move_raw.product_id
            unit = move_raw.uom_id
            if summary['model'] == 'to_order':
                bom = move_raw.product_id.bom_ids[:1]
                if bom and bom.type == 'subcontract':
                    result.append(self._make_components_line(summary, product, quantity, unit, bom, level, current_index))
            elif summary['model'] == 'purchase.order':
                po = self.env[summary['model']].browse(summary['id'])
                move = po.order_line.move_ids.filtered(lambda m: m.product_id.id == move_raw.product_id.id and m.is_subcontract)
                bom = move_raw.product_id.bom_ids[:1]
                subcontracted_mo = move.move_orig_ids.production_id
                if subcontracted_mo:
                    subcontracted_mo = self._contextualized_production(subcontracted_mo)
                    components = self._get_components_data(subcontracted_mo, replenish_data=replenish_data, level=level + 1, current_index=current_index)
                    result[0]['components'] = components
                    result[0]['operations'] = {'details': [], 'summary': {'index': ''}}
                    result[0]['byproducts'] = {'details': [], 'summary': {'index': ''}}
                    result[0]['subcontracted'] = True
                elif bom and bom.type == 'subcontract' and po.partner_id in bom.subcontractor_ids:
                    result.append(self._make_components_line(summary, product, quantity, unit, bom, level, current_index))
        return result

    def _make_components_line(self, summary, product, quantity, unit, bom, level, index):
        bom_price = product._compute_bom_price(bom)
        seller_price = product._select_seller(quantity=quantity, uom_id=unit, params={'subcontractor_ids': bom.subcontractor_ids}).price
        components_cost = quantity * (bom_price - seller_price)
        components_line = {'summary': {
            'level': level + 1,
            'index': f"{index}C",
            'name': _("Components"),
            'model': "components",
            'uom_precision': self._get_uom_precision(bom.uom_id.rounding),
            'unit_cost': summary['currency'].round(components_cost / quantity),
            'mo_cost': summary['currency'].round(components_cost),
            'bom_cost': summary['currency'].round(components_cost),
            'currency_id': summary['currency_id'],
            'currency': summary['currency'],
        }}
        summary['bom_cost'] = summary['currency'].round(quantity * seller_price)
        summary['mo_cost_decorator'] = self._get_comparison_decorator(summary['bom_cost'], summary['mo_cost'], 0.01)
        summary['subcontracted'] = True
        return components_line

    def _get_component_bom_cost(self, move_raw, quantity, doc_in=False):
        if doc_in and doc_in._name == 'purchase.order':
            bom = move_raw.product_id.bom_ids[:1]
            if bom and bom.type == 'subcontract' and doc_in.partner_id in bom.subcontractor_ids:
                seller_price = move_raw.product_id._select_seller(quantity=quantity, uom_id=move_raw.uom_id, params={'subcontractor_ids': bom.subcontractor_ids}).price
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
