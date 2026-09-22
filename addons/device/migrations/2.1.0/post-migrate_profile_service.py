import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists
from odoo.libs.sql import SQL

_logger = logging.getLogger(__name__)

AUTH_TYPES = {"token": "bearer", "oauth": "oauth2"}
OLD_COLUMNS = ("endpoint", "port", "http_timeout", "auth_type", "auth_username")


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    columns = [c for c in OLD_COLUMNS if column_exists(cr, "device_profile", c)]
    selected = ", ".join(columns) or "NULL"
    cr.execute(
        f"SELECT id, protocol, credential_id, {selected} FROM device_profile ORDER BY id"
    )
    rows = cr.fetchall()
    profiles = env["device.profile"].with_context(active_test=False)
    for row in rows:
        profile = profiles.browse(row[0])
        old = dict(zip(columns, row[3:], strict=True))
        scheme = "https" if row[1] == "https" else "http"
        endpoint_url = False
        if old.get("endpoint"):
            endpoint_url = f"{scheme}://{old['endpoint']}"
            if old.get("port"):
                endpoint_url += f":{old['port']}"
        service = profile._ensure_service(
            {
                "auth_type": AUTH_TYPES.get(old.get("auth_type"), old.get("auth_type")),
                "endpoint_url": endpoint_url,
                "http_timeout": old.get("http_timeout"),
            }
        )
        credential = env["credential.credential"].browse(row[2]).exists()
        if credential:
            vals = {}
            if not credential.endpoint_id:
                vals["endpoint_id"] = service.id
            if old.get("auth_username") and not credential.username:
                vals["username"] = old["auth_username"]
            if vals:
                credential.write(vals)
    _logger.info("device 19.0.2.1.0: %s profile(s) carry their service", len(rows))
    for column in columns:
        cr.execute(
            SQL("ALTER TABLE device_profile DROP COLUMN %s", SQL.identifier(column))
        )
    devices = env["device.device"].with_context(active_test=False).search([])
    devices._sync_connection()
    # The one service every device used to dial through keeps its exchange
    # history and stops being offered.
    shared = env.ref("device.service_iot_device", raise_if_not_found=False)
    if shared:
        shared.write({"active": False})
    _logger.info(
        "device 19.0.2.1.0: %s device(s) dial through a connection",
        len(devices.filtered("connection_id")),
    )
