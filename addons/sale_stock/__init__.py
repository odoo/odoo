# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo.fields import Domain


def _split_partial_sale_order_lines(env):
    """ Pre-init hook: before installing stock, split partial order lines
    so that there's no unnecessary stock trigger. """
    to_adjust = Domain.AND([
        Domain('state', '=', 'sale'),
        Domain('delivery_status', '=', 'partial')
    ])
    partial_orders = env['sale.order'].search([to_adjust])
    lines_to_create = []

    for line in partial_orders.order_line:
        if 0 < line.qty_delivered < line.product_uom_qty:
            new_line = line.copy_data({
                'order_id': line.order_id.id,
                'product_uom_qty': line.product_uom_qty - line.qty_delivered,
            })
            line.product_uom_qty = line.qty_delivered
            lines_to_create.extend(new_line)
    if lines_to_create:
        env['sale.order.line'].create(lines_to_create)


def _create_pickings_for_open_sale_orders(env):
    """ Upon installing stock create pickings for all open SOs (confirmed but not delivered). """
    to_adjust = Domain.AND([
        Domain('state', '=', 'sale'),
        Domain('delivery_status', '!=', 'full')
    ])
    open_sale_orders = env['sale.order'].search([to_adjust])
    partial_orders = open_sale_orders.filtered(lambda o: o.delivery_status == 'partial')
    empty_lines = open_sale_orders.order_line.filtered(lambda l: l.product_uom_id.is_zero(l.qty_delivered))
    if empty_lines:
        empty_lines._compute_qty_delivered_method()
        empty_lines._action_launch_stock_rule()
    partial_orders.delivery_status = 'partial'  # because the delivery_status is recomputed based on pickings state
