import logging

_logger = logging.getLogger(__name__)

_GROUP_MERGES = (
    ("group_api_gateway_user", "group_api_transport_user"),
    ("group_api_gateway_admin", "group_api_transport_admin"),
)

_PARAM_MOVES = (
    ("api_gateway.log_retention_days", "integration.log_retention_days"),
    ("api_gateway.max_cache_entries", "integration.max_cache_entries"),
)

_PARAM_DROPS = (
    "api_gateway.enable_global_logging",
    "api_gateway.redact_sensitive",
    "api_gateway.session_cache_size",
    "api_gateway.session_cache_ttl",
)


def _group_id(cr, name):
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'integration' AND model = 'res.groups' AND name = %s
        """,
        (name,),
    )
    row = cr.fetchone()
    return row[0] if row else None


def _merge_groups(cr):
    carried = 0
    for old_name, new_name in _GROUP_MERGES:
        old_id = _group_id(cr, old_name)
        new_id = _group_id(cr, new_name)
        if not old_id or not new_id:
            continue

        cr.execute(
            """
            INSERT INTO res_groups_users_rel (gid, uid)
            SELECT %s, old.uid
              FROM res_groups_users_rel old
             WHERE old.gid = %s
            ON CONFLICT DO NOTHING
            """,
            (new_id, old_id),
        )
        carried += cr.rowcount

        cr.execute("DELETE FROM ir_model_access WHERE group_id = %s", (old_id,))
        cr.execute(
            "DELETE FROM res_groups_implied_rel WHERE gid = %s OR hid = %s",
            (old_id, old_id),
        )
        cr.execute("DELETE FROM res_groups_users_rel WHERE gid = %s", (old_id,))
        cr.execute("DELETE FROM rule_group_rel WHERE group_id = %s", (old_id,))
        cr.execute("DELETE FROM res_groups WHERE id = %s", (old_id,))
        cr.execute(
            """
            DELETE FROM ir_model_data
             WHERE module = 'integration' AND model = 'res.groups' AND name = %s
            """,
            (old_name,),
        )
        _logger.info(
            "19.0.1.7.0: merged integration.%s into integration.%s",
            old_name,
            new_name,
        )

    return carried


def _drop_privilege(cr):
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'integration'
           AND model = 'res.groups.privilege'
           AND name = 'res_groups_privilege_api_gateway'
        """
    )
    row = cr.fetchone()
    if not row:
        return

    cr.execute("DELETE FROM res_groups_privilege WHERE id = %s", (row[0],))
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'integration'
           AND model = 'res.groups.privilege'
           AND name = 'res_groups_privilege_api_gateway'
        """
    )
    _logger.info("19.0.1.7.0: dropped the API Gateway privilege")


def _move_parameters(cr):
    moved = 0
    for old_key, new_key in _PARAM_MOVES:
        cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", (old_key,))
        row = cr.fetchone()
        if not row:
            continue

        cr.execute(
            """
            INSERT INTO ir_config_parameter (key, value)
                 VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (new_key, row[0]),
        )
        cr.execute("DELETE FROM ir_config_parameter WHERE key = %s", (old_key,))
        moved += 1
        _logger.info("19.0.1.7.0: %s = %s carried onto %s", old_key, row[0], new_key)

    cr.execute(
        "DELETE FROM ir_config_parameter WHERE key = ANY(%s)", (list(_PARAM_DROPS),)
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.7.0: deleted %s api_gateway setting(s) that had no reader",
            cr.rowcount,
        )

    return moved


def migrate(cr, version):
    carried = _merge_groups(cr)
    _drop_privilege(cr)
    moved = _move_parameters(cr)

    _logger.info(
        "19.0.1.7.0: carried %s group membership(s) onto the transport tier and "
        "%s configured setting(s) onto the keys that are read.",
        carried,
        moved,
    )
