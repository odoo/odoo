# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report

from odoo import api, SUPERUSER_ID

def _create_warehouse_data(cr, registry):
    """ This hook is used to add a default manufacture_pull_id, manufacture
    picking_type on every warehouse. It is necessary if the mrp module is
    installed after some warehouses were already created.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouse_ids = env['stock.warehouse'].search([('manufacture_pull_id', '=', False)])
    for warehouse_id in warehouse_ids:
        warehouse_id.write({'manufacture_to_resupply': True})
