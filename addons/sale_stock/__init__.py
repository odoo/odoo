# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo.fields import Domain


def _create_pickings_for_open_sale_orders(env):
    """ Upon installing stock create pickings for all open (confirmed but not delivered/received)
        SO/PO. If any lines are partially done, split them.
    """
    to_adjust = Domain.AND([
        Domain('state', '=', 'sale'),
        Domain('delivery_status', '!=', 'full')
    ])
    open_sale_orders = env['sale.order'].search([to_adjust])
    partial_orders = env['sale.order']
    empty_lines = env['sale.order.line']
    lines_to_create = []

    for so in open_sale_orders:
        if so.delivery_status == 'partial':
            partial_orders |= so
        for line in so.order_line:
            if 0 < line.qty_delivered < line.product_uom_qty:
                new_line = line.copy_data({
                    'order_id': line.order_id.id,
                    'product_uom_qty': line.product_uom_qty - line.qty_delivered,
                })
                lines_to_create.extend(new_line)
                line.with_context(skip_procurement=True).product_uom_qty = line.qty_delivered
            elif line.product_uom_id.is_zero(line.qty_delivered):
                empty_lines |= line
    if empty_lines:
        empty_lines._compute_qty_delivered_method()
        empty_lines._action_launch_stock_rule()
    if lines_to_create:
        env['sale.order.line'].create(lines_to_create)  # Also triggers _action_launch_stock_rule
    partial_orders.delivery_status = 'partial'
