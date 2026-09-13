from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.module.module"].search(
        [("name", "=", "automation_webhook"), ("state", "=", "uninstalled")]
    ).button_install()
