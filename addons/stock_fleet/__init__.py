from . import models


def _enable_dispatch_management(env):
    for delivery_steps, warehouses in env['stock.warehouse']._read_group([], ['delivery_steps'], ['id:recordset']):
        if delivery_steps == 'pick_pack_ship':
            warehouses.pack_type_id.dispatch_management = True
        elif delivery_steps == 'pick_ship':
            warehouses.pick_type_id.dispatch_management = True

        warehouses.out_type_id.dispatch_management = True
        warehouses.in_type_id.dispatch_management = True
