# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    stock_move_count = fields.Integer(compute='_compute_stock_move_count')

    def _compute_stock_move_count(self):
        stock_move_read_group = self.env['stock.move']._read_group([('sale_line_id', 'in', self.ids)], ['sale_line_id'], ['sale_line_id'])
        stock_move_count_per_sol = {res['sale_line_id'][0]: res['sale_line_id_count'] for res in stock_move_read_group}
        for sol in self:
            sol.stock_move_count = stock_move_count_per_sol.get(sol.id, 0)

    def _get_action_per_item(self):
        """ Get action per Sales Order Item to display the stock moves linked

            :returns: Dict containing id of SOL as key and the action as value
        """
        action_per_sol = super()._get_action_per_item()
        stock_move_action = self.env.ref('sale_project_stock.stock_move_per_sale_order_line_action').id
        for sol in self:
            if not sol.is_service and sol.stock_move_count > 0:
                action_per_sol[sol.id] = stock_move_action
        return action_per_sol
