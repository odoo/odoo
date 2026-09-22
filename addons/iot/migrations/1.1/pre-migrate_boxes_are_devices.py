"""An IoT box and each thing it carries become rows of the device registry.

The rows are made here, before the model loads, because `device_id` is
required: the loader would otherwise meet a table full of rows and an empty
column. The kinds are assigned in the post-migration, since the records that
name them are loaded with this module's data, after this runs.
"""

import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists

from odoo.addons.iot.models.iot_box import REGISTRY_DEFAULTS

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    if not table_exists(cr, "iot_box"):
        return
    for table in ("iot_box", "iot_device"):
        if not column_exists(cr, table, "device_id"):
            cr.execute(f"ALTER TABLE {table} ADD COLUMN device_id integer")

    env = api.Environment(cr, SUPERUSER_ID, {})
    devices = env["device.device"]

    cr.execute(
        "SELECT id, name, identifier, company_id, ip FROM iot_box "
        "WHERE device_id IS NULL ORDER BY id"
    )
    boxes = cr.fetchall()
    device_of_box = {}
    for box_id, name, identifier, company_id, ip in boxes:
        device = devices.create(
            {
                "name": name or identifier or f"IoT Box {box_id}",
                "identifier": identifier,
                "company_id": company_id,
                "endpoint": ip,
                **REGISTRY_DEFAULTS,
            }
        )
        device_of_box[box_id] = device.id
        cr.execute(
            "UPDATE iot_box SET device_id = %s WHERE id = %s", [device.id, box_id]
        )

    cr.execute(
        "SELECT id, iot_id, name, identifier, connected_status FROM iot_device "
        "WHERE device_id IS NULL ORDER BY id"
    )
    for row_id, box_id, name, identifier, connected in cr.fetchall():
        parent = device_of_box.get(box_id)
        if parent is None:
            cr.execute("SELECT device_id FROM iot_box WHERE id = %s", [box_id])
            parent = (cr.fetchone() or [None])[0]
        device = devices.create(
            {
                "name": name or identifier or f"IoT Device {row_id}",
                "identifier": identifier,
                "parent_id": parent,
                "company_id": devices.browse(parent).company_id.id if parent else False,
                "connection_state": connected or "disconnected",
                **REGISTRY_DEFAULTS,
            }
        )
        cr.execute(
            "UPDATE iot_device SET device_id = %s WHERE id = %s", [device.id, row_id]
        )

    for table in ("iot_box", "iot_device"):
        cr.execute(f"SELECT count(*) FROM {table} WHERE device_id IS NULL")
        if cr.fetchone()[0]:
            continue
        cr.execute(f"ALTER TABLE {table} ALTER COLUMN device_id SET NOT NULL")

    _logger.info(
        "IoT registry: %s box(es) and their devices are device.device rows",
        len(boxes),
    )
