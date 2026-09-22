from odoo import SUPERUSER_ID, api

PLACEHOLDER_URL = "https://unconfigured.invalid/"


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    service = env.ref("device.service_iot_device", raise_if_not_found=False)
    if not service:
        return
    vals = {"per_record_connections": True}
    if service.endpoint_url == PLACEHOLDER_URL:
        vals["endpoint_url"] = False
    service.write(vals)
