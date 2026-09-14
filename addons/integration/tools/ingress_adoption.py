import logging

_logger = logging.getLogger(__name__)

_PREVIOUS_OWNER = "credential"

_ADOPTED_NAMES = (
    "model_mixin_inbound_gate",
    "model_inbound_access_log",
    "model_inherit__mixin_inbound_gate__mixin_credential_auth",
    "access_inbound_access_log_user",
    "access_inbound_access_log_admin",
    "view_inbound_access_log_list",
    "view_inbound_access_log_search",
    "action_inbound_access_log",
    "menu_inbound_access_logs",
    "ir_cron_gc_inbound_access_logs",
    "ir_cron_gc_inbound_access_logs_ir_actions_server",
)

_ADOPTED_PREFIXES = (
    "field_mixin_inbound_gate__",
    "field_inbound_access_log__",
    "selection__inbound_access_log__",
    "constraint_inbound_access_log_",
)


def adopt_ingress_from_credential(cr) -> int:
    cr.execute(
        """
        SELECT 1 FROM ir_model_data
         WHERE module = %s AND name = 'model_inbound_access_log'
        """,
        (_PREVIOUS_OWNER,),
    )
    if not cr.fetchone():
        return 0

    patterns = [f"{prefix}%" for prefix in _ADOPTED_PREFIXES]
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'integration'
           AND (name = ANY(%s) OR name LIKE ANY(%s))
        """,
        (list(_ADOPTED_NAMES), patterns),
    )
    cr.execute(
        """
        UPDATE ir_model_data SET module = 'integration'
         WHERE module = %s
           AND (name = ANY(%s) OR name LIKE ANY(%s))
        """,
        (_PREVIOUS_OWNER, list(_ADOPTED_NAMES), patterns),
    )
    adopted = cr.rowcount
    cr.execute(
        """
        UPDATE ir_model_constraint
           SET module = (SELECT id FROM ir_module_module WHERE name = 'integration')
         WHERE model IN (
                   SELECT id FROM ir_model
                    WHERE model IN ('inbound.access.log', 'mixin.inbound.gate')
               )
           AND module = (SELECT id FROM ir_module_module WHERE name = %s)
        """,
        (_PREVIOUS_OWNER,),
    )
    _logger.info(
        "integration: adopted %s inbound gate record(s) from %s",
        adopted,
        _PREVIOUS_OWNER,
    )
    return adopted
