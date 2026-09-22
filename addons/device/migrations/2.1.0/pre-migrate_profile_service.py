from odoo.db.schema import column_exists
from odoo.tools.module_data import rename_field


def migrate(cr, version):
    if not version:
        return
    if column_exists(cr, "device_profile", "auth_credential_id"):
        rename_field(cr, "device.profile", "auth_credential_id", "credential_id")
