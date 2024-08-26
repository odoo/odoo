from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        res = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom)
        if values.get('sale_line_id'):
            res['sale_line_id'] = values['sale_line_id']
        return res

    def _prepare_procurement_values(self, move_vals, product, old_values):
        res = super()._prepare_procurement_values(move_vals, product, old_values)
        if move_vals.get('sale_line_id'):
            so = self.env['sale.order.line'].browse(move_vals['sale_line_id']).order_id
            res['analytic_account_id'] = so.analytic_account_id
            if so.analytic_account_id:
                res['analytic_distribution'] = {so.analytic_account_id.id: 100}
        return res
