def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'remote_config' AND column_name = 'auth_password'"
    )
    if cr.fetchone():
        cr.execute(
            "ALTER TABLE remote_config RENAME COLUMN auth_password TO legacy_auth_password"
        )
        cr.execute(
            "ALTER TABLE remote_config RENAME COLUMN auth_token TO legacy_auth_token"
        )
