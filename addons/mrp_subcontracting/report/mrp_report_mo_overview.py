from odoo import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _include_pdf_specifics(self, doc, data=None):
        result = super()._include_pdf_specifics(doc, data)
        if result['show_availabilities'] and result['summary'].get('is_subcontract'):
            result['footer_colspan'] += 1
        return result

    def _get_mo_summary(self, production, components, current_mo_cost, remaining_cost_share):
        data = super()._get_mo_summary(production, components, current_mo_cost, remaining_cost_share)
        if production.subcontractor_id:
            data['is_subcontract'] = True
        return data

    def _should_get_component_replenishment(self, production, move_raw):
        return not (
            production.subcontractor_id
            and move_raw.rule_id.procure_method == 'make_to_stock'
        )

    def _get_components_data(self, production, replenish_data=False, level=0, current_index=False):
        components = super()._get_components_data(production, replenish_data, level, current_index)
        if production.subcontractor_id and production.state != 'done' and components:
            self_ctx = self.with_context(warehouse_location=True)
            warehouse_replenish_data = None
            for count, move_raw in enumerate(production.move_raw_ids):
                if components[count]['replenishments'] and self._should_get_component_replenishment(production, move_raw) and production.picking_ids:
                    if warehouse_replenish_data is None:
                        warehouse_replenish_data = self_ctx._get_replenish_data(production)
                    component_index = f"{current_index}{count + 1}"
                    replenishments = self_ctx._get_replenishment_lines(
                        production, move_raw, warehouse_replenish_data, level, component_index,
                    )
                    if replenishments and replenishments[0]['summary']['model'] == 'to_order':
                        components[count]['summary'].update({
                            'state': 'to_order',
                            'formatted_state': self.env._("To Order"),
                        })
                    components[count]['replenishments'] += replenishments
        return components

    def _format_component_move(self, production, move_raw, replenishments, replenish_data, level, index):
        data = super()._format_component_move(production, move_raw, replenishments, replenish_data, level, index)
        if production.subcontractor_id:
            product = move_raw.product_id.with_context(location=production.location_src_id.id)
            if (move_raw.procure_method != 'make_to_stock'):
                data['receipt'] = self._check_planned_start(
                    production.date_start, self._get_component_receipt(product, move_raw, replenishments, replenish_data),
                )
            if product.is_storable:
                data['subcontract_free_qty'] = product.uom_id._compute_quantity(
                    max(product.free_qty, 0), move_raw.uom_id,
                )
                data['subcontract_qty_on_hand'] = product.uom_id._compute_quantity(
                    product.qty_available, move_raw.uom_id,
                )
        return data

    def _get_location_ids(self, production, replenish_data):
        if production.subcontractor_id:
            if self.env.context.get('warehouse_location'):
                return production.picking_ids[0].location_id.ids
            return self.env['stock.location'].search_fetch([('id', 'child_of', production.location_src_id.id)], ['id']).ids
        return super()._get_location_ids(production, replenish_data)
