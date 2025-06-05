from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        res = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom)
        if values.get('sale_line_id'):
            res['sale_line_id'] = values['sale_line_id']
        return res

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        if (sol_id := values.get('sale_line_id')) is not None and 'product_id' in move_values:
            # if the SOL is for a kit
            if move_values['product_id'] != self.env['sale.order.line'].browse(sol_id).product_id.id:
                bom_line_id = self.env['sale.order.line'].browse(sol_id).move_ids.bom_line_id.filtered(
                    lambda bl: bl.product_id.id == move_values.get('product_id')
                ).id
                if bom_line_id:
                    move_values['bom_line_id'] = bom_line_id
        return move_values
