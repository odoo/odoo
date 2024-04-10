import time

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    manufactured_num_products = fields.Float(compute='_compute_product_margin_fields_values', string='# Manufactured Products',
        help="Sum of Quantity in Manufacturing Orders")

    def _compute_product_margin_fields_values(self):
        res = super()._compute_product_margin_fields_values()
        date_from = self.env.context.get('date_from', time.strftime('%Y-01-01'))
        date_to = self.env.context.get('date_to', time.strftime('%Y-12-31'))
        for product in self:
            product_id = product.id
            res[product_id]['manufactured_num_products'] = 0
            manufacture_orders = self.env['mrp.production'].search([
                ('product_id', '=', product_id),
                ('state', '=', 'done'),
                ('date_start', '>=', date_from),
                ('date_finished', '<=', date_to)
            ])
            total_manufacture_cost = 0
            nos_of_products_manufactured = 0
            if manufacture_orders:
                for order in manufacture_orders:
                    res1 = self.env['report.mrp.report_mo_overview'].get_report_values(production_id=order.id)
                    total_manufacture_cost = total_manufacture_cost + res1['data']['summary']['mo_cost']
                    nos_of_products_manufactured = nos_of_products_manufactured + res1['data']['summary']['quantity']
                    if order.scrap_count > 0:
                        scrap_orders = self.env['stock.scrap'].search([('production_id', '=', order.id), ('product_id', '=', product_id)])
                        scrap_quantities = 0
                        for scrap_order in scrap_orders:
                            scrap_quantities = scrap_quantities + scrap_order.scrap_qty
                        nos_of_products_manufactured = nos_of_products_manufactured - scrap_quantities
            res[product_id]['total_cost'] += total_manufacture_cost
            res[product_id]['manufactured_num_products'] = nos_of_products_manufactured
            res[product_id]['total_margin'] -= total_manufacture_cost
            res[product_id]['total_margin_rate'] -= res[product_id].get('turnover', 0.0) and total_manufacture_cost * 100 / res[product_id].get('turnover', 0.0) or 0.0
            product.update(res[product.id])
        return res
