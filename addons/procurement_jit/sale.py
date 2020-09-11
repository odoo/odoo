# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        res = super(SaleOrderLine, self)._action_launch_stock_rule(previous_product_uom_qty=previous_product_uom_qty)
        orders = list(set(x.order_id for x in self))
        for order in orders:
            reassign = order.picking_ids.filtered(lambda x: x.state=='confirmed' or (x.state in ['waiting', 'assigned'] and not x.printed))
            if reassign:
                # Trigger the Scheduler for Pickings
                reassign.action_confirm()
                reassign.action_assign()
        return res
