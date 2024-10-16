from odoo import models
from odoo.addons import stock_landed_costs, mrp_subcontracting


class StockMove(stock_landed_costs.StockMove, mrp_subcontracting.StockMove):

    def _get_stock_valuation_layer_ids(self):
        self.ensure_one()
        stock_valuation_layer_ids = super()._get_stock_valuation_layer_ids()
        subcontracted_productions = self._get_subcontract_production()
        if self.is_subcontract and subcontracted_productions:
            return subcontracted_productions.move_finished_ids.stock_valuation_layer_ids
        return stock_valuation_layer_ids
