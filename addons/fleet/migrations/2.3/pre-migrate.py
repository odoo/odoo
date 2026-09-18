from odoo.addons.fleet.table_inheritance import (
    create_vehicle_table,
    move_vehicles_into_their_table,
)


def migrate(cr, version):
    create_vehicle_table(cr)
    move_vehicles_into_their_table(cr)
