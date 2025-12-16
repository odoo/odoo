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
        Domain('delivery_status', '!=', "full")
    ])
    open_sale_orders = env["sale.order"].search([to_adjust])
    lines_to_create = []
    for so in open_sale_orders:
        for line in so.order_line:
            partial_procurement = 0 < line.qty_delivered < line.product_uom_qty
            if line.qty_delivered != line.product_uom_qty and not partial_procurement:
                line._action_launch_stock_rule()
            elif partial_procurement:
                lines_to_create.append(
                    {
                        "order_id": line.order_id.id,
                        "product_id": line.product_id.id,
                        "product_uom_qty": line.product_uom_qty - line.qty_delivered,
                    }
                )
                line.product_uom_qty = line.qty_delivered
    if lines_to_create:
        env["sale.order.line"].create(lines_to_create)  # Also triggers _action_launch_stock_rule
