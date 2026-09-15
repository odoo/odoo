from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if not version or not table_exists(cr, "maintenance_equipment"):
        return
    if column_exists(cr, "maintenance_equipment", "location_id") and column_exists(
        cr, "resource_asset", "location_id"
    ):
        cr.execute(
            """
            UPDATE resource_asset asset
               SET location_id = equipment.location_id
              FROM maintenance_equipment equipment
             WHERE equipment.asset_id = asset.id
               AND equipment.location_id IS NOT NULL
               AND asset.location_id IS NULL
            """
        )
    cr.execute("DROP TABLE maintenance_equipment CASCADE")
    if table_exists(cr, "maintenance_equipment_category"):
        cr.execute("DROP TABLE maintenance_equipment_category CASCADE")
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    env.invalidate_all()
    cr.execute("SELECT DISTINCT resource_id FROM maintenance_order_resource_rel")
    resources = env["resource.resource"].browse([row[0] for row in cr.fetchall()])
    for name in ("maintenance_count", "maintenance_open_count"):
        env.add_to_compute(resources._fields[name], resources)
    resources.flush_recordset(["maintenance_count", "maintenance_open_count"])
