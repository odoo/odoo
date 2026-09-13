from odoo import models


class ReportMrpReport_Bom_Structure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_bom_data(self, bom, warehouse, product=False, line_qty=False, bom_line=False, level=0, parent_bom=False, parent_product=False, index=0, product_info=False, ignore_stock=False, simulated_leaves_per_workcenter=False):
        res = super()._get_bom_data(bom, warehouse, product, line_qty, bom_line, level, parent_bom, parent_product, index, product_info, ignore_stock, simulated_leaves_per_workcenter)
        res['bom_type'] = bom.type
        res['bom_extra_cost'] = bom.extra_cost
        res['price_precision'] = self.env['decimal.precision'].precision_get('Product Price')
        res['product_precision'] = self.env['decimal.precision'].precision_get('Product Unit')
        if bom.type == 'normal':
            res['bom_cost'] += bom.extra_cost * line_qty
            res['bom_unit_cost'] += bom.extra_cost * line_qty
        return res

    def _get_bom_array_lines(self, data, level, unfolded_ids, unfolded, parent_unfolded=True):
        res = super()._get_bom_array_lines(data, level, unfolded_ids, unfolded, parent_unfolded)
        if data['bom_type'] == 'normal' and data['bom_extra_cost'] > 0:
            res.append({
                'bom_cost': data['bom_extra_cost'] * data['quantity'],
                'forecast_mode': False,
                'level': data['level'],
                'name': 'Extra Cost',
                'producible_qty': False,
                'quantity': data['quantity'],
                'type': 'bom',
                'uom': data['uom_name'],
                'visible': True,
            })
        return res
