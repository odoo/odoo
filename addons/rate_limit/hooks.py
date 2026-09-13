import logging

from odoo import api

_logger = logging.getLogger(__name__)

_PREVIOUS_OWNER = "credential"

_ADOPTED_NAMES = (
    "model_rate_limit_bucket",
    "access_rate_limit_bucket_admin",
    "rate_limit_bucket_company_rule",
    "constraint_rate_limit_bucket_bucket_key_uniq",
    "view_rate_limit_bucket_search",
    "view_rate_limit_bucket_list",
    "view_rate_limit_bucket_form",
    "action_rate_limit_bucket",
    "menu_rate_limit_bucket",
    "ir_cron_cleanup_old_buckets",
    "ir_cron_cleanup_old_buckets_ir_actions_server",
    "ir_cron_cleanup_rate_limiter",
    "ir_cron_cleanup_rate_limiter_ir_actions_server",
)

_ADOPTED_PREFIXES = ("field_rate_limit_bucket__",)

_CRONS = {
    "ir_cron_cleanup_old_buckets": (
        "Rate Limit: Cleanup Old Buckets",
        "model.cron_gc_old_buckets()",
    ),
    "ir_cron_cleanup_rate_limiter": (
        "Rate Limit: Cleanup In-Memory Caller Limiter",
        "model.cron_cleanup_caller_rate_limiter()",
    ),
}


def adopt_from_credential(cr) -> int:
    cr.execute(
        """
        SELECT 1 FROM ir_model_data
         WHERE module = %s AND name = 'model_rate_limit_bucket'
        """,
        (_PREVIOUS_OWNER,),
    )
    if not cr.fetchone():
        return 0

    prefix_patterns = [f"{prefix}%" for prefix in _ADOPTED_PREFIXES]
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'rate_limit'
           AND (name = ANY(%s) OR name LIKE ANY(%s))
        """,
        (list(_ADOPTED_NAMES), prefix_patterns),
    )
    cr.execute(
        """
        UPDATE ir_model_data SET module = 'rate_limit'
         WHERE module = %s
           AND (name = ANY(%s) OR name LIKE ANY(%s))
        """,
        (_PREVIOUS_OWNER, list(_ADOPTED_NAMES), prefix_patterns),
    )
    adopted = cr.rowcount

    cr.execute(
        """
        UPDATE ir_model_constraint
           SET module = (SELECT id FROM ir_module_module WHERE name = 'rate_limit')
         WHERE model = (SELECT id FROM ir_model WHERE model = 'rate.limit.bucket')
           AND module = (SELECT id FROM ir_module_module WHERE name = %s)
        """,
        (_PREVIOUS_OWNER,),
    )

    cr.execute("SELECT id FROM ir_model WHERE model = 'rate.limit.bucket'")
    (bucket_model_id,) = cr.fetchone()
    for cron_xmlid, (name, code) in _CRONS.items():
        cr.execute(
            """
            SELECT c.id, c.ir_actions_server_id
              FROM ir_cron c
              JOIN ir_model_data d
                ON d.res_id = c.id
               AND d.model = 'ir.cron'
               AND d.module = 'rate_limit'
               AND d.name = %s
            """,
            (cron_xmlid,),
        )
        for cron_id, action_id in cr.fetchall():
            cr.execute(
                """
                UPDATE ir_act_server
                   SET model_id = %s,
                       code = %s,
                       name = jsonb_set(
                           COALESCE(name, '{}'::jsonb), '{en_US}', to_jsonb(%s::text)
                       )
                 WHERE id = %s
                """,
                (bucket_model_id, code, name, action_id),
            )
            cr.execute(
                "UPDATE ir_cron SET cron_name = %s WHERE id = %s", (name, cron_id)
            )

    _logger.info("rate_limit: adopted %s record(s) from %s", adopted, _PREVIOUS_OWNER)
    return adopted


def pre_init_hook(env: api.Environment) -> None:
    adopt_from_credential(env.cr)
