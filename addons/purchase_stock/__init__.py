# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard


def _create_buy_rules(env):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('buy_pull_id', '=', False)])
    warehouse_ids.write({'buy_to_resupply': True})
