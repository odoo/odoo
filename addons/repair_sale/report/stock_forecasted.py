from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _product_sale_domain(self, product_template_ids, product_ids):
        """
        When a product's move is bind at the same time to a Repair Order
        and to a Sale Order, only take the data into account once, as a RO
        """
        sol_domain = super()._product_sale_domain(product_template_ids, product_ids)
        move_domain = self._product_domain(product_template_ids, product_ids)
        move_domain += [
            ('repair_id', '!=', False),
            ('sale_line_id', '!=', False),
            ('repair_line_type', '=', 'add')
        ]
        sol_ids = self.env['stock.move']._read_group(move_domain, aggregates=['sale_line_id:array_agg'])[0][0]

        sol_domain += [('id', 'not in', sol_ids)]
        return sol_domain
