import logging

_logger = logging.getLogger(__name__)

_COLUMNS = {
    "credential_credential": "service_id",
    "integration_response_cache": "service_id",
}

_MODULES = (
    "integration",
    "api_ai",
    "api_ai_agent",
    "telegram_bot",
    "telegram_bot_approval_request",
    "api_github",
    "api_odoo_rpc",
    "ai_claude",
)


def _rename_columns(cr):
    for table, column in _COLUMNS.items():
        cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s
               AND column_name = %s
            """,
            (table, column),
        )
        if not cr.fetchone():
            continue

        cr.execute(f'ALTER TABLE "{table}" RENAME COLUMN {column} TO endpoint_id')

        cr.execute(
            """
            SELECT indexname
              FROM pg_indexes
             WHERE tablename = %s
               AND indexname LIKE %s
            """,
            (table, f"%{column}%"),
        )
        for (indexname,) in cr.fetchall():
            cr.execute(
                f'ALTER INDEX "{indexname}" RENAME TO '
                f'"{indexname.replace(column, "endpoint_id")}"'
            )

        cr.execute(
            """
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = %s::regclass
               AND conname LIKE %s
            """,
            (table, f"%{column}%"),
        )
        for (conname,) in cr.fetchall():
            cr.execute(
                f'ALTER TABLE "{table}" RENAME CONSTRAINT "{conname}" TO '
                f'"{conname.replace(column, "endpoint_id")}"'
            )

        _logger.info(
            "19.0.1.10.0: %s.%s renamed to endpoint_id, matching the "
            "integration.service model it has always pointed at.",
            table,
            column,
        )


def _rename_in_stored_arch(cr):
    cr.execute(
        """
        UPDATE ir_ui_view v
           SET arch_db = replace(v.arch_db::text, 'service_id', 'endpoint_id')::jsonb
          FROM ir_model_data d
         WHERE d.model = 'ir.ui.view'
           AND d.res_id = v.id
           AND d.module = ANY(%s)
           AND v.arch_db::text LIKE '%%service_id%%'
        """,
        (list(_MODULES),),
    )
    if cr.rowcount:
        _logger.info("19.0.1.10.0: rewrote %s stored view arch(s).", cr.rowcount)

    for table, model_column, columns in (
        ("ir_act_window", "res_model", ("domain", "context")),
        ("ir_filters", "model_id", ("domain", "context")),
    ):
        for column in columns:
            cr.execute(
                f"""
                UPDATE {table} t
                   SET {column} = replace(t.{column}, 'service_id', 'endpoint_id')
                 WHERE t.{column} LIKE %s
                   AND t.{model_column} IN (
                         'credential.credential',
                         'credential.access.log',
                         'integration.response.cache',
                         'ai.provider'
                       )
                """,
                ("%service_id%",),
            )
            if cr.rowcount:
                _logger.info(
                    "19.0.1.10.0: rewrote %s %s.%s value(s).",
                    cr.rowcount,
                    table,
                    column,
                )

    cr.execute(
        """
        UPDATE ir_rule r
           SET domain_force = replace(r.domain_force, 'service_id', 'endpoint_id')
          FROM ir_model_data d
         WHERE d.model = 'ir.rule'
           AND d.res_id = r.id
           AND d.module = ANY(%s)
           AND r.domain_force LIKE '%%service_id%%'
        """,
        (list(_MODULES),),
    )
    if cr.rowcount:
        _logger.info("19.0.1.10.0: rewrote %s record rule domain(s).", cr.rowcount)


def migrate(cr, version):
    _rename_columns(cr)
    _rename_in_stored_arch(cr)
