# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import populate
from . import wizard


def _create_buy_rules(env):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    all_warehouses = env['stock.warehouse'].search([])
    buy_route = env['stock.route'].search([]).filtered(lambda r: set(r.rule_ids.mapped('action')) == {'buy'})
    if buy_route:
        buy_route.warehouse_ids |= all_warehouses

    warehouse_ids = all_warehouses.filtered(lambda w: not w.buy_pull_id)
    warehouse_ids.write({'buy_to_resupply': True})
