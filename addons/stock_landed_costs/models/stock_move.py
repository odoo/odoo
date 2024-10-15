from odoo import models
from odoo.addons import purchase_stock, stock_account


class StockMove(stock_account.StockMove, purchase_stock.StockMove):

    def _get_stock_valuation_layer_ids(self):
        self.ensure_one()
        return self.stock_valuation_layer_ids
