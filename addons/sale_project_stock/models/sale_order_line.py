# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_action_per_item(self):
        """ Get action per Sales Order Item to display the stock moves linked

            :returns: Dict containing id of SOL as key and the action as value
        """
        action_per_sol = super()._get_action_per_item()
        stock_move_action = self.env.ref('sale_project_stock.stock_move_per_sale_order_line_action').id
        stock_move_ids_per_sol = {}
        if self.env.user.has_group('stock.group_stock_user'):
            stock_move_read_group = self.env['stock.move']._read_group([('sale_line_id', 'in', self.ids)], ['sale_line_id'], ['id:array_agg'])
            stock_move_ids_per_sol = {sale_line.id: ids for sale_line, ids in stock_move_read_group}
        for sol in self:
            stock_move_ids = stock_move_ids_per_sol.get(sol.id, [])
            if not sol.is_service and stock_move_ids:
                action_per_sol[sol.id] = stock_move_action, stock_move_ids[0] if len(stock_move_ids) == 1 else False
        return action_per_sol
