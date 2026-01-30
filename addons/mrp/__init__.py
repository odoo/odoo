# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report
from . import controller
from . import populate

from odoo import api, SUPERUSER_ID


def _pre_init_mrp(cr):
    """ Allow installing MRP in databases with large stock.move table (>1M records)
        - Creating the computed+stored field stock_move.is_done and
          stock_move.unit_factor is terribly slow with the ORM and leads to "Out of
          Memory" crashes
    """
    cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "is_done" bool;""")
    cr.execute("""UPDATE stock_move
                     SET is_done=COALESCE(state in ('done', 'cancel'), FALSE);""")
    cr.execute('ALTER TABLE stock_move ADD COLUMN IF NOT EXISTS unit_factor double precision DEFAULT 1')
    # `stock.move.bom_line_id` is created in this module, so its default value will be NULL.
    # `stock.move._is_manual_consumption` always returns False when there is no `bom_line_id`;
    # therefore, we can just initialize `manual_consumption` to FALSE by default.
    env.cr.execute('ALTER TABLE stock_move ADD COLUMN IF NOT EXISTS manual_consumption bool DEFAULT FALSE')

def _create_warehouse_data(cr, registry):
    """ This hook is used to add a default manufacture_pull_id, manufacture
    picking_type on every warehouse. It is necessary if the mrp module is
    installed after some warehouses were already created.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouse_ids = env['stock.warehouse'].search([('manufacture_pull_id', '=', False)])
    warehouse_ids.write({'manufacture_to_resupply': True})

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouses = env["stock.warehouse"].search([])
    pbm_routes = warehouses.mapped("pbm_route_id")
    warehouses.write({"pbm_route_id": False})
    # Fail unlink means that the route is used somewhere (e.g. route_id on stock.rule). In this case
    # we don't try to do anything.
    try:
        with env.cr.savepoint():
            pbm_routes.unlink()
    except:
        pass
