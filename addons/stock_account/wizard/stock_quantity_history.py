# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_at_date(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'stock.valuation.layer':
            action = self.env.ref('stock_account.stock_valuation_layer_action').read()[0]
            action['domain'] = [('create_date', '<=', self.inventory_datetime)]
            action['display_name'] = str(self.inventory_datetime)
            return action

        return super(StockQuantityHistory, self).open_at_date()
