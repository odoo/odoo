# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report
from . import controller


def _pre_init_mrp(env):
    """ Allow installing MRP in databases with large stock.move table (>1M records)
<<<<<<< 511c634c87f4a98bbf6aca1205b52ad12c9f6f1a
        - Creating the computed stored fields `stock_move` `unit_factor` and `manual_consumption`
        is terribly slow with the ORM and leads to "Out of Memory" crashes.
||||||| cd5f29b8b50ef4228be8f58a02bb328548208f77
        - Creating the computed+stored field stock_move.is_done and
          stock_move.unit_factor is terribly slow with the ORM and leads to "Out of
          Memory" crashes
=======
        - Creating the computed+stored field stock.move.is_done, stock.move.unit_factor
          and stock.move.manual_consumption is terribly slow with the ORM and leads to "Out of
          Memory" crashes
>>>>>>> 37d1a207341e675aa6db8d6f7db9f17b274edbba
    """
<<<<<<< 511c634c87f4a98bbf6aca1205b52ad12c9f6f1a
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "unit_factor" double precision NOT NULL DEFAULT 1;""")
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "manual_consumption" boolean NOT NULL DEFAULT FALSE;""")
||||||| cd5f29b8b50ef4228be8f58a02bb328548208f77
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "is_done" bool;""")
    env.cr.execute("""UPDATE stock_move
                     SET is_done=COALESCE(state in ('done', 'cancel'), FALSE);""")
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "unit_factor" double precision;""")
    env.cr.execute("""UPDATE stock_move
                     SET unit_factor=1;""")
=======
    def install_stock_move__is_done():
        # On a long-lived database, there are more moves that are in an end state than not,
        # so we initialize all as `is_done IS TRUE` first and only update those that are not afterward.
        env.cr.execute('ALTER TABLE stock_move ADD COLUMN IF NOT EXISTS is_done bool DEFAULT TRUE')
        # Where clause is same as `state NOT IN ('done', 'cancel')`, but inverted to hit the index on `state`
        env.cr.execute("""
           UPDATE stock_move
              SET is_done = FALSE
            WHERE state IN ('draft', 'waiting', 'confirmed', 'partially_available', 'assigned')
        """)

    def install_stock_move__unit_factor():
        env.cr.execute('ALTER TABLE stock_move ADD COLUMN IF NOT EXISTS unit_factor double precision DEFAULT 1')

    def install_stock_move__manual_consumption():
        # `stock.move.bom_line_id` is created in this module, so its default value will be NULL.
        # `stock.move._is_manual_consumption` always returns False when there is no `bom_line_id`;
        # therefore, we can just initialize `manual_consumption` to FALSE by default.
        env.cr.execute('ALTER TABLE stock_move ADD COLUMN IF NOT EXISTS manual_consumption bool DEFAULT FALSE')

    install_stock_move__is_done()
    install_stock_move__unit_factor()
    install_stock_move__manual_consumption()

>>>>>>> 37d1a207341e675aa6db8d6f7db9f17b274edbba

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
