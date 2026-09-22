import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'remote_device' AND column_name = 'auto_reconnect'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        ALTER TABLE remote_device
        ADD COLUMN IF NOT EXISTS auto_reconnect_override VARCHAR
        """
    )
    cr.execute(
        """
        UPDATE remote_device
        SET auto_reconnect_override = 'on'
        WHERE auto_reconnect IS TRUE AND auto_reconnect_override IS NULL
        """
    )
    migrated = cr.rowcount
    cr.execute("ALTER TABLE remote_device DROP COLUMN auto_reconnect")
    _logger.info(
        "19.0.1.4.0: %s device(s) carried an explicit auto-reconnect override; "
        "the rest now inherit their configuration profile and can be switched "
        "off individually.",
        migrated,
    )
