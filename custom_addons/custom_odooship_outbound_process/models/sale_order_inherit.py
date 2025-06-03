# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields,api
from collections import Counter

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial_number = fields.Char(string="Serial Number")
    line_item_id = fields.Char(string="Line Item ID")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    message_code = fields.Integer(string='Message code')
    discrete_pick = fields.Boolean(string="Merge Order", default=False, copy=False)
    automation_manual_order = fields.Selection([
        ('automation', 'Automation'),
        ('manual', 'Manual'),
        ('cross_dock', 'Cross Dock'),
        ('automation_bulk', 'Automation Bulk'),
        ('automation_putaway', 'Automation Putaway')
    ], string="Automation/Manual Order", compute="_compute_process_type_selection", store=True)

    @api.depends('order_line.route_id.routes_process_selection_types', 'discrete_pick')
    def _compute_process_type_selection(self):
        for order in self:
            # If discrete, clear the process type selection
            if order.discrete_pick:
                order.automation_manual_order = False
                continue
            # Gather all process types from the order line routes
            process_types = set(order.order_line.mapped('route_id.routes_process_selection_types'))
            process_types.discard(False)
            if len(process_types) == 1:
                order.automation_manual_order = process_types.pop()
            else:
                order.automation_manual_order = False  # Ambiguous or missing

    @api.model
    def create(self, vals):
        order = super().create(vals)
        order._compute_discrete_pick_flag()
        # order._compute_process_type_selection()
        return order

    def action_confirm(self):
        res = super().action_confirm()
        self._compute_discrete_pick_flag()
        # self._compute_process_type_selection()
        return res

    def _compute_discrete_pick_flag(self):
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ('cancel',)
                          and getattr(p.picking_type_id, 'picking_process_type', 'pick') == 'pick'
            )
            if len(pickings) > 1:
                order.discrete_pick = True
            else:
                order.discrete_pick = False
            for pick in pickings:
                pick.discrete_pick = order.discrete_pick
                pick.automation_manual_order = order.automation_manual_order