import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'gateway_ml_provider'
           AND column_name = 'service_id'
        """
    )
    if not cr.fetchone():
        _logger.info(
            "19.0.1.6.0: gateway_ml_provider.service_id is already gone; nothing to rename."
        )
        return

    cr.execute("ALTER TABLE gateway_ml_provider RENAME COLUMN service_id TO endpoint_id")
    cr.execute(
        """
        SELECT indexname
          FROM pg_indexes
         WHERE tablename = 'gateway_ml_provider'
           AND indexname LIKE '%%service_id%%'
        """
    )
    for (indexname,) in cr.fetchall():
        cr.execute(
            "ALTER INDEX %s RENAME TO %s"
            % (indexname, indexname.replace("service_id", "endpoint_id"))
        )

    _logger.info(
        "19.0.1.6.0: gateway_ml_provider.service_id renamed to endpoint_id, the "
        "_inherits delegate included."
    )
