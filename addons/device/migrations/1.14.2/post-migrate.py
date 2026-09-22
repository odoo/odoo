from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'device_profile' AND column_name = 'legacy_auth_password'"
    )
    if not cr.fetchone():
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        "SELECT id, legacy_auth_password, legacy_auth_token FROM device_profile "
        "WHERE legacy_auth_password IS NOT NULL OR legacy_auth_token IS NOT NULL"
    )
    for config_id, password, token in cr.fetchall():
        config = env["device.profile"].with_context(active_test=False).browse(config_id)
        vals = {}
        if password:
            vals["auth_password"] = password
        if token:
            vals["auth_token"] = token
        config.write(vals)
    env.flush_all()
    cr.execute(
        "ALTER TABLE device_profile DROP COLUMN legacy_auth_password, "
        "DROP COLUMN legacy_auth_token"
    )
