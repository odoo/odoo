from odoo import models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _get_related_product(self):
        res = super()._get_related_product()
        return self.stock_move_id.sale_line_id.product_id if self.stock_move_id.sale_line_id else res
