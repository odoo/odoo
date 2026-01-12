# Copyright 2025 XCG
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
def migrate(cr, version):
    cr.execute(
        "SELECT true FROM pg_attribute WHERE attrelid = 'fs_storage'::regclass AND "
        "attname = 'check_connection_method' AND NOT attisdropped;"
    )
    if cr.fetchall():
        cr.execute(
            """UPDATE fs_storage
            SET server_env_defaults = (('{"x_check_connection_method_env_default": "' ||
            check_connection_method || '"}')::jsonb || server_env_defaults::jsonb)::text
            ;"""
        )
        # clean up
        cr.execute("ALTER TABLE fs_storage DROP COLUMN check_connection_method;")
