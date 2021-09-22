# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.misc import format_datetime


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_at_date(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'stock.valuation.layer':
            action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
            action['domain'] = [('create_date', '<=', self.inventory_datetime), ('product_id.type', '=', 'product')]
            action['display_name'] = format_datetime(self.env, self.inventory_datetime)
            return action

        return super(StockQuantityHistory, self).open_at_date()
