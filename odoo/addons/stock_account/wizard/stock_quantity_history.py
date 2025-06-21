# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.misc import format_datetime


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_at_date(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'stock.valuation.layer':
            action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
            # views may not exist in stable => use auto-created ones in this case
            tree_view = self.env.ref('stock_account.stock_valuation_layer_valuation_at_date_tree_inherited', raise_if_not_found=False)
            graph_view = self.env.ref('stock_account.stock_valuation_layer_graph', raise_if_not_found=False)
            action['views'] = [(tree_view.id if tree_view else False, 'tree'),
                               (self.env.ref('stock_account.stock_valuation_layer_form').id, 'form'),
                               (self.env.ref('stock_account.stock_valuation_layer_pivot').id, 'pivot'),
                               (graph_view.id if graph_view else False, 'graph')]
            action['domain'] = [('create_date', '<=', self.inventory_datetime), ('product_id.type', '=', 'product')]
            action['display_name'] = format_datetime(self.env, self.inventory_datetime)
            action['context'] = "{}"
            return action

        return super(StockQuantityHistory, self).open_at_date()
