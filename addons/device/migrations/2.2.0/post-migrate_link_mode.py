import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists
from odoo.libs.sql import SQL

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    # The ORM proposed a mode from the protocol and the address; a kind that
    # says how its devices link (device_mobile, device_machines, ...) writes
    # it as it loads and the devices follow through the dependency.
    devices = env["device.device"].with_context(active_test=False).search([])
    devices._sync_connection()
    _logger.info(
        "device 19.0.2.2.0: %s device(s); %s dialled, %s pushing, %s streamed",
        len(devices),
        len(devices.filtered(lambda d: d.link_mode == "pull")),
        len(devices.filtered(lambda d: d.link_mode == "push")),
        len(devices.filtered(lambda d: d.link_mode == "stream")),
    )
    for column in ("reconnect_failures", "date_next_reconnect"):
        if column_exists(cr, "device_device", column):
            cr.execute(
                SQL("ALTER TABLE device_device DROP COLUMN %s", SQL.identifier(column))
            )
