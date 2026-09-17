from . import models
from . import wizards


def _create_warehouse_data(env):
    for warehouse in env["stock.warehouse"].search(
        [("maintenance_type_id", "=", False)]
    ):
        picking_type_vals = warehouse._create_or_update_picking_types()
        if picking_type_vals:
            warehouse.write(picking_type_vals)
