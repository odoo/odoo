from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_stock_valuation_layer_ids(self):
        self.ensure_one()
        stock_valuation_layer_ids = super()._get_stock_valuation_layer_ids()
        subcontracted_productions = self._get_subcontract_production()
        if self.is_subcontract and subcontracted_productions:
            return subcontracted_productions.move_finished_ids.stock_valuation_layer_ids
        return stock_valuation_layer_ids
