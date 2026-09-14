import logging

_logger = logging.getLogger(__name__)

_OLD_MODEL = "comm.response.cache"
_NEW_MODEL = "integration.response.cache"
_OLD_TABLE = "comm_response_cache"
_NEW_TABLE = "integration_response_cache"

_RENAMED = {
    "group_comm_user": "group_api_transport_user",
    "group_comm_manager": "group_api_transport_manager",
    "group_comm_admin": "group_api_transport_admin",
    "comm_root": "integration_root",
    "comm_services": "integration_services",
    "comm_config": "integration_config",
}

_RENAMED_PREFIXES = {
    "comm_response_cache": "integration_response_cache",
    "access_comm_response_cache": "access_integration_response_cache",
    "rule_comm_response_cache": "rule_integration_response_cache",
}


def migrate(cr, version):
    _rename_table(cr)
    _rename_model_rows(cr)
    _rename_xmlids(cr)


def _rename_table(cr):
    cr.execute("SELECT to_regclass(%s)", (_OLD_TABLE,))
    if not cr.fetchone()[0]:
        _logger.info("%s already renamed, nothing to do", _OLD_TABLE)
        return

    cr.execute(f'ALTER TABLE "{_OLD_TABLE}" RENAME TO "{_NEW_TABLE}"')
    _logger.info("renamed table %s -> %s", _OLD_TABLE, _NEW_TABLE)

    cr.execute(
        """
        SELECT indexname FROM pg_indexes
        WHERE tablename = %s AND indexname LIKE %s
        """,
        (_NEW_TABLE, f"{_OLD_TABLE}%"),
    )
    for (index_name,) in cr.fetchall():
        new_name = index_name.replace(_OLD_TABLE, _NEW_TABLE, 1)
        cr.execute(f'ALTER INDEX "{index_name}" RENAME TO "{new_name}"')
        _logger.info("renamed index %s -> %s", index_name, new_name)

    cr.execute("SELECT to_regclass(%s)", (f"{_OLD_TABLE}_id_seq",))
    if cr.fetchone()[0]:
        cr.execute(
            f'ALTER SEQUENCE "{_OLD_TABLE}_id_seq" RENAME TO "{_NEW_TABLE}_id_seq"'
        )


def _rename_model_rows(cr):
    cr.execute(
        "UPDATE ir_model SET model = %s WHERE model = %s",
        (_NEW_MODEL, _OLD_MODEL),
    )
    if cr.rowcount:
        _logger.info("ir_model: %s -> %s", _OLD_MODEL, _NEW_MODEL)

    cr.execute(
        "UPDATE ir_model_fields SET model = %s WHERE model = %s",
        (_NEW_MODEL, _OLD_MODEL),
    )
    cr.execute(
        "UPDATE ir_model_data SET model = %s WHERE model = %s",
        (_NEW_MODEL, _OLD_MODEL),
    )
    cr.execute(
        """
        UPDATE ir_model_data
        SET name = %s
        WHERE module = 'integration' AND model = 'ir.model' AND name = %s
        """,
        (f"model_{_NEW_TABLE}", f"model_{_OLD_TABLE}"),
    )
    cr.execute(
        """
        UPDATE ir_model_data
        SET name = replace(name, %s, %s)
        WHERE module = 'integration'
          AND model = 'ir.model.fields'
          AND name LIKE %s
        """,
        (f"field_{_OLD_TABLE}", f"field_{_NEW_TABLE}", f"field_{_OLD_TABLE}%"),
    )

    for table, column in (
        ("ir_act_window", "res_model"),
        ("ir_ui_view", "model"),
        ("ir_rule", "model_id"),
    ):
        if column == "model_id":
            continue
        cr.execute("SELECT to_regclass(%s)", (table,))
        if not cr.fetchone()[0]:
            continue
        cr.execute(
            f"UPDATE {table} SET {column} = %s WHERE {column} = %s",
            (_NEW_MODEL, _OLD_MODEL),
        )
        if cr.rowcount:
            _logger.info("%s.%s: %d row(s) repointed", table, column, cr.rowcount)


def _rename_xmlids(cr):
    for old, new in _RENAMED.items():
        cr.execute(
            """
            UPDATE ir_model_data SET name = %s
            WHERE module = 'integration' AND name = %s
              AND NOT EXISTS (
                  SELECT 1 FROM ir_model_data
                  WHERE module = 'integration' AND name = %s
              )
            """,
            (new, old, new),
        )
        if cr.rowcount:
            _logger.info("xmlid integration.%s -> %s", old, new)

    for old_prefix, new_prefix in _RENAMED_PREFIXES.items():
        cr.execute(
            """
            UPDATE ir_model_data
            SET name = %s || substring(name from %s)
            WHERE module = 'integration' AND name LIKE %s
            """,
            (new_prefix, len(old_prefix) + 1, f"{old_prefix}%"),
        )
        if cr.rowcount:
            _logger.info(
                "xmlid prefix %s -> %s on %d row(s)",
                old_prefix,
                new_prefix,
                cr.rowcount,
            )
