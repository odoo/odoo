from odoo.addons.fleet.table_inheritance import (
    create_vehicle_table,
    move_vehicles_into_their_table,
    name_the_vehicle_model,
)


def migrate(cr, version):
    # On an install `pre_init_hook` does this; on an upgrade there is no hook,
    # and the rows already exist in the parent table and have to come across.
    create_vehicle_table(cr)
    name_the_vehicle_model(cr)
    move_vehicles_into_their_table(cr)
