# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_table(self):
        if not self.env.context.get('valuation'):
            return super(StockQuantityHistory, self).open_table()

        action = self.env.ref('stock_account.stock_valuation_layer_action').read()[0]
        if int(self.compute_at_date):
            action['domain'] = [('create_date', '<=', self.date)]
            return action
        else:
            return action

