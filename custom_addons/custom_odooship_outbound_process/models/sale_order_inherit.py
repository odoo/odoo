# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields,api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial_number = fields.Char(string="Serial Number")
    line_item_id = fields.Char(string="Line Item ID")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    message_code = fields.Integer(string='Message code')
    discrete_pick = fields.Boolean(string="Discrete Order", default=False, copy=False)

    @api.model
    def create(self, vals):
        order = super().create(vals)
        order._compute_discrete_pick_flag()
        return order

    def action_confirm(self):
        res = super().action_confirm()
        self._compute_discrete_pick_flag()
        return res

    def _compute_discrete_pick_flag(self):
        for order in self:
            # Filter pickings not cancelled and of process type 'pick'
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ('cancel',)
                          and p.picking_type_id.picking_process_type == 'pick'
            )
            # Mark discrete if there are more than one 'pick' process pickings
            if len(pickings) > 1:
                order.discrete_pick = True
            else:
                order.discrete_pick = False
            # Set discrete_pick on each of those pickings as well
            for pick in pickings:
                pick.discrete_pick = order.discrete_pick

