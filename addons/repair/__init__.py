# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report


def _create_warehouse_data(env):
    """ This hook is used to add default repair picking types on every warehouse.
    It is necessary if the repair module is installed after some warehouses were already created.
    """
    warehouses = env['stock.warehouse'].search([('repair_type_id', '=', False)])
    for warehouse in warehouses:
        picking_type_vals = warehouse._create_or_update_sequences_and_picking_types()
        if picking_type_vals:
            warehouse.write(picking_type_vals)
