import logging

_logger = logging.getLogger(__name__)

_STALE_GATEWAY_CRONS = (
    "cron_health_check_services",
    "cron_reset_cache_errors",
    "cron_check_expiring_credentials",
)


def migrate(cr, version):
    cr.execute("SELECT count(*) FROM ir_module_module WHERE name = 'api_gateway'")
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        DELETE FROM ir_cron
         WHERE id IN (
               SELECT res_id FROM ir_model_data
                WHERE module = 'api_gateway'
                  AND model = 'ir.cron'
                  AND name = ANY(%s)
         )
        """,
        (list(_STALE_GATEWAY_CRONS),),
    )
    crons = cr.rowcount
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'api_gateway'
           AND model = 'ir.cron'
           AND name = ANY(%s)
        """,
        (list(_STALE_GATEWAY_CRONS),),
    )

    cr.execute(
        """
        DELETE FROM ir_model_data gw
         WHERE gw.module = 'api_gateway'
           AND EXISTS (
               SELECT 1 FROM ir_model_data mine
                WHERE mine.module = 'integration'
                  AND mine.name = gw.name
           )
        """
    )
    dropped = cr.rowcount

    cr.execute(
        "UPDATE ir_model_data SET module = 'integration' WHERE module = 'api_gateway'"
    )
    adopted = cr.rowcount

    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'uninstalled', db_version = NULL
         WHERE name = 'api_gateway'
        """
    )
    cr.execute("DELETE FROM ir_module_module_dependency WHERE name = 'api_gateway'")

    _logger.info(
        "19.0.1.6.0: adopted %s ir_model_data row(s) from api_gateway, dropped "
        "%s already owned here, purged %s stale cron(s), and marked the module "
        "uninstalled.",
        adopted,
        dropped,
        crons,
    )
