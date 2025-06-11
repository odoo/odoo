# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report
from . import controller
from . import populate


def _pre_init_mrp(env):
    """ Allow installing MRP in databases with large stock.move table (>1M records)
        - Creating the computed+stored field stock_move.is_done and
          stock_move.unit_factor is terribly slow with the ORM and leads to "Out of
          Memory" crashes
    """
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "is_done" bool DEFAULT TRUE;""")
    env.cr.execute("""UPDATE stock_move
                    SET is_done = FALSE
                  WHERE state NOT IN ('done', 'cancel');""")
    env.cr.execute("""ALTER TABLE stock_move ALTER COLUMN is_done DROP DEFAULT;""")
    env.cr.execute("""ALTER TABLE "stock_move"
                    ADD COLUMN "unit_factor" double precision DEFAULT 1;""")
    env.cr.execute("""ALTER TABLE stock_move ALTER COLUMN unit_factor DROP DEFAULT;""")

def _create_warehouse_data(env):
    """ This hook is used to add a default manufacture_pull_id, manufacture
    picking_type on every warehouse. It is necessary if the mrp module is
    installed after some warehouses were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('manufacture_pull_id', '=', False)])
    warehouse_ids.write({'manufacture_to_resupply': True})

def uninstall_hook(env):
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
