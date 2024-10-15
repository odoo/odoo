# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import stock_landed_costs


class StockValuationAdjustmentLines(stock_landed_costs.StockValuationAdjustmentLines):

    def _prepare_account_move_line_values(self):
        res = super()._prepare_account_move_line_values()
        if self.cost_id.target_model == 'picking':
            res['analytic_distribution'] = self.move_id.picking_id.project_id._get_analytic_distribution()
        return res
