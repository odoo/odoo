# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report

from odoo import api, SUPERUSER_ID


def _create_buy_rules(cr, registry):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouse_ids = env['stock.warehouse'].search([('buy_pull_id', '=', False)])
    for warehouse_id in warehouse_ids:
        warehouse_id._create_or_update_global_routes_rules()
