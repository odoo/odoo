"""Each registry row takes the kind its old selection named.

The kind records load with this module's data, so this cannot happen in the
pre-migration that made the rows.
"""

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if not version or not table_exists(cr, "iot_box"):
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    box_kind = env.ref("iot.kind_iot_box", raise_if_not_found=False)
    if box_kind:
        cr.execute(
            "UPDATE device_device d SET device_category_id = %s FROM iot_box b "
            "WHERE b.device_id = d.id AND d.device_category_id IS NULL",
            [box_kind.id],
        )
    if not column_exists(cr, "iot_device", "type"):
        return
    cr.execute("SELECT DISTINCT type FROM iot_device WHERE type IS NOT NULL")
    for (value,) in cr.fetchall():
        kind = env.ref(f"iot.kind_iot_{value}", raise_if_not_found=False)
        if not kind:
            continue
        cr.execute(
            "UPDATE device_device d SET device_category_id = %s FROM iot_device i "
            "WHERE i.device_id = d.id AND i.type = %s AND d.device_category_id IS NULL",
            [kind.id, value],
        )
