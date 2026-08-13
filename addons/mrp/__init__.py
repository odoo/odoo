# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report
from . import controller


def _pre_init_mrp(env):
    """ Allow installing MRP in databases with large stock.move table (>1M records)
        - Creating the computed+stored field stock.move.is_done, stock.move.unit_factor
          and stock.move.manual_consumption is terribly slow with the ORM and leads to "Out of
          Memory" crashes
    """
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
