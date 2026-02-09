# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from odoo.fields import Domain


def post_init_hook(env):
    _create_buy_rules(env)
    _create_pickings_for_open_purchase_orders(env)


def _create_buy_rules(env):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('buy_pull_id', '=', False)])
    warehouse_ids.write({'buy_to_resupply': True})


def _create_pickings_for_open_purchase_orders(env):
    """ Upon installing stock create pickings for all open (confirmed but not delivered/received)
        SO/PO. If any lines are partially done, split them.
    """
    to_adjust = Domain.AND([
        Domain('state', '=', 'purchase'),
        Domain('receipt_status', '!=', "full")
    ])
    open_purchase_orders = env["purchase.order"].search([to_adjust])
    lines_to_create = []
    for po in open_purchase_orders:
        for line in po.order_line:
            partial_procurement = 0 < line.qty_received < line.product_uom_qty
            if line.qty_received != line.product_uom_qty and not partial_procurement:
                line._create_or_update_picking()
            elif partial_procurement:
                lines_to_create.append(
                    {
                        "order_id": line.order_id.id,
                        "product_id": line.product_id.id,
                        "product_uom_qty": line.product_uom_qty - line.qty_received,
                        "product_uom_id": line.product_uom_id,
                    }
                )
                line.product_qty = line.qty_received
    if lines_to_create:
        env["purchase.order.line"].create(lines_to_create)  # Also triggers _create_or_update_picking
