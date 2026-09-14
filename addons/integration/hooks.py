import logging

from .tools.ingress_adoption import adopt_ingress_from_credential

_logger = logging.getLogger(__name__)

_OLD = "api_communication"
_NEW = "integration"

_RENAMED_XMLIDS = {
    "module_category_api_communication": "module_category_api_transport",
    "res_groups_privilege_api_communication": "res_groups_privilege_api_transport",
    "group_comm_user": "group_api_transport_user",
    "group_comm_manager": "group_api_transport_manager",
    "group_comm_admin": "group_api_transport_admin",
}

_PARAM_SUFFIXES = [
    "retry_batch_size",
    "retry_processing_timeout",
    "log_retention_days",
    "max_cache_entries",
    "max_payload_size_limit",
    "max_duplicate_window_seconds",
    "timestamp_future_tolerance",
    "allow_none_signature",
]


def _takeover_module_row(env) -> bool:
    env.cr.execute(
        "SELECT state FROM ir_module_module WHERE name = %s AND state <> ALL(%s)",
        (_OLD, ["uninstalled", "uninstallable", "to remove"]),
    )
    row = env.cr.fetchone()
    if not row:
        return False

    env.cr.execute(
        "UPDATE ir_module_module SET state = 'uninstalled' WHERE name = %s",
        (_OLD,),
    )
    _logger.info(
        "integration: taking over %s (was state=%s); its records are being "
        "re-tagged to this module and its tables are left untouched",
        _OLD,
        row[0],
    )
    return True


def _retag_model_data(env) -> None:
    for old_name, new_name in _RENAMED_XMLIDS.items():
        env.cr.execute(
            "UPDATE ir_model_data SET module = %s, name = %s "
            "WHERE module = %s AND name = %s",
            (_NEW, new_name, _OLD, old_name),
        )
        if env.cr.rowcount:
            _logger.info("integration: %s.%s -> %s.%s", _OLD, old_name, _NEW, new_name)

    env.cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s", (_NEW, _OLD)
    )
    if env.cr.rowcount:
        _logger.info(
            "integration: re-tagged %s ir_model_data row(s) from %s",
            env.cr.rowcount,
            _OLD,
        )


_BACKUP_TABLE = "integration_param_takeover"


def _rename_config_parameters(env) -> None:
    for suffix in _PARAM_SUFFIXES:
        env.cr.execute(
            """
            UPDATE ir_config_parameter
               SET key = %(new)s
             WHERE key = %(old)s
               AND NOT EXISTS (
                     SELECT 1 FROM ir_config_parameter WHERE key = %(new)s
                   )
            """,
            {"new": f"{_NEW}.{suffix}", "old": f"{_OLD}.{suffix}"},
        )
        if env.cr.rowcount:
            _logger.info(
                "integration: carried %s.%s over to %s.%s",
                _OLD,
                suffix,
                _NEW,
                suffix,
            )

    env.cr.execute(
        f"CREATE TABLE IF NOT EXISTS {_BACKUP_TABLE} "
        "(key varchar PRIMARY KEY, value text)"
    )
    env.cr.execute(
        f"INSERT INTO {_BACKUP_TABLE} (key, value) "
        "SELECT key, value FROM ir_config_parameter WHERE key = ANY(%s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        ([f"{_NEW}.{s}" for s in _PARAM_SUFFIXES],),
    )
    if env.cr.rowcount:
        _logger.info(
            "integration: stashed %s system parameter value(s) for post_init "
            "to restore after the init-mode data load overwrites them",
            env.cr.rowcount,
        )


_GATEWAY = "api_gateway"

_GATEWAY_ENDPOINT_OWNERS = {
    "service_custom_api": _NEW,
    "service_stripe": _NEW,
    "service_twilio": _NEW,
    "service_github": "api_github",
    "service_telegram": "telegram_bot",
    "service_odoo_database_template": _NEW,
}


def _adopt_gateway_endpoints(env) -> int:
    adopted = 0
    for name, owner in _GATEWAY_ENDPOINT_OWNERS.items():
        env.cr.execute(
            """
            UPDATE ir_model_data d
               SET module = %(owner)s
             WHERE d.module = %(old)s
               AND d.model = 'integration.service'
               AND d.name = %(name)s
               AND NOT EXISTS (
                     SELECT 1 FROM ir_model_data e
                      WHERE e.module = %(owner)s
                        AND e.model = d.model
                        AND e.name = d.name
                   )
            """,
            {"owner": owner, "old": _GATEWAY, "name": name},
        )
        if env.cr.rowcount:
            adopted += env.cr.rowcount
            _logger.info("integration: %s.%s -> %s.%s", _GATEWAY, name, owner, name)
    if adopted:
        _logger.info(
            "integration: routed %s outbound endpoint(s) out of %s to their new owners",
            adopted,
            _GATEWAY,
        )
    return adopted


def pre_init_hook(env):
    adopt_ingress_from_credential(env.cr)
    if _takeover_module_row(env):
        _retag_model_data(env)
        _rename_config_parameters(env)
    _adopt_gateway_endpoints(env)


def post_init_hook(env):
    env.cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (_BACKUP_TABLE,),
    )
    if not env.cr.fetchone():
        return

    env.flush_all()
    env.cr.execute(
        f"""
        UPDATE ir_config_parameter p
           SET value = b.value
          FROM {_BACKUP_TABLE} b
         WHERE p.key = b.key
           AND p.value IS DISTINCT FROM b.value
        """
    )
    restored = env.cr.rowcount
    env.cr.execute(f"DROP TABLE {_BACKUP_TABLE}")
    env.invalidate_all()

    if restored:
        _logger.info(
            "integration: restored %s system parameter value(s) that the "
            "init-mode data load had reset to shipped defaults",
            restored,
        )
