from odoo import SUPERUSER_ID, api

APP_MENU_MARKER = "sale.migration_app_menu_visible"


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    marker = env["ir.config_parameter"].search([("key", "=", APP_MENU_MARKER)])
    if not marker:
        return
    env.ref("base.group_user").implied_ids |= env.ref("sale.group_sale_app_menu")
    marker.unlink()
