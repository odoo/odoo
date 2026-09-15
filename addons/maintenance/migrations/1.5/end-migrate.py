from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    env.invalidate_all()
    cr.execute("SELECT DISTINCT resource_id FROM maintenance_order_resource_rel")
    resources = env["resource.resource"].browse(row[0] for row in cr.fetchall())
    if not resources:
        return
    Resource = env["resource.resource"]
    for name in ("maintenance_count", "maintenance_open_count"):
        env.add_to_compute(Resource._fields[name], resources)
    resources.flush_recordset(["maintenance_count", "maintenance_open_count"])
