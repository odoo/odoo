from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_stock_valuation_layer_ids(self):
        self.ensure_one()
        return super()._get_stock_valuation_layer_ids()
