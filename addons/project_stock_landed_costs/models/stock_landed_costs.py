# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockValuationAdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    def _prepare_account_move_line_values(self):
        res = super()._prepare_account_move_line_values()
        if self.cost_id.target_model == 'picking':
            res['analytic_distribution'] = self.move_id.picking_id.project_id._get_analytic_distribution()
        return res
