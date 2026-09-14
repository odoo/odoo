import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cr.fetchone() is not None


def migrate(cr, version):
    if not version:
        return
    if not _column_exists(cr, "remote_device", "token_fingerprint"):
        return
    if _column_exists(cr, "remote_device", "credential_fingerprint"):
        cr.execute(
            """
            UPDATE remote_device
            SET credential_fingerprint = token_fingerprint
            WHERE credential_fingerprint IS NULL AND token_fingerprint IS NOT NULL
            """
        )
        cr.execute("ALTER TABLE remote_device DROP COLUMN token_fingerprint")
        _logger.info(
            "19.0.1.3.0: merged remote_device.token_fingerprint into "
            "credential_fingerprint (%s row(s)).",
            cr.rowcount,
        )
        return
    cr.execute(
        "ALTER TABLE remote_device RENAME COLUMN token_fingerprint "
        "TO credential_fingerprint"
    )
    cr.execute('DROP INDEX IF EXISTS "remote_device__token_fingerprint_index"')
    _logger.info(
        "19.0.1.3.0: renamed remote_device.token_fingerprint to "
        "credential_fingerprint; every device keeps authenticating."
    )
