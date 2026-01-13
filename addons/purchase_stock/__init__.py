# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from odoo.fields import Domain


def _post_init_hook(env):
    _create_buy_rules(env)
    _create_pickings_for_open_purchase_orders(env)


def _split_partial_purchase_order_lines(env):
    """ Pre-init hook: before installing stock, split partial order lines
    so that there's no unnecessary stock trigger. """
    to_adjust = Domain.AND([
        Domain('state', '=', 'purchase'),
        Domain('receipt_status', '=', 'partial')
    ])
    partial_orders = env['purchase.order'].search([to_adjust])
    lines_to_create = []

    for line in partial_orders.order_line:
        if 0 < line.qty_received < line.product_qty:
            new_line = line.copy_data({
                'product_qty': line.product_qty - line.qty_received,
            })
            lines_to_create.extend(new_line)
            line.product_qty = line.qty_received
    if lines_to_create:
        env['purchase.order.line'].create(lines_to_create)


def _create_buy_rules(env):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('buy_pull_id', '=', False)])
    warehouse_ids.write({'buy_to_resupply': True})


def _create_pickings_for_open_purchase_orders(env):
    """ Upon installing stock create pickings for all open POs (confirmed but not received). """
    to_adjust = Domain.AND([
        Domain('state', '=', 'purchase'),
        Domain('receipt_status', '!=', 'full')
    ])
    open_purchase_orders = env['purchase.order'].search([to_adjust])
    partial_orders = open_purchase_orders.filtered(lambda o: o.receipt_status == 'partial')
    empty_lines = open_purchase_orders.order_line.filtered(lambda l: l.uom_id.is_zero(l.qty_received))
    if empty_lines:
        empty_lines._compute_qty_received_method()
        empty_lines._set_date_promised()
        empty_lines._create_or_update_picking()
    partial_orders.receipt_status = 'partial'   # because the delivery_status is recomputed based on pickings state
