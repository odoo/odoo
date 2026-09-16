from . import models
from . import report

from odoo import Command


def _enable_dispatch_management(env):
    group_stock_picking_batch = env.ref('stock.group_stock_picking_batch')
    env.ref('base.group_user').write({'implied_ids': [Command.link(group_stock_picking_batch.id)]})

    for delivery_steps, warehouses in env['stock.warehouse']._read_group([], ['delivery_steps'], ['id:recordset']):
        if delivery_steps == 'pick_pack_ship':
            warehouses.pack_type_id.dispatch_management = True
        elif delivery_steps == 'pick_ship':
            warehouses.pick_type_id.dispatch_management = True

        warehouses.out_type_id.dispatch_management = True
        warehouses.in_type_id.dispatch_management = True
