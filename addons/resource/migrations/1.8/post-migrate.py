import logging

_logger = logging.getLogger(__name__)

# Both rules live in a `noupdate="1"` block, so no upgrade has ever rewritten
# them: `security/resource_security.xml` was corrected upstream while every
# database that installed `resource` before the correction kept the old rows.
REPAIRS = (
    (
        "resource_schedule_exception_rule_group_user_modify",
        "resource.schedule.exception: employee modifies own",
        "[('resource_id.user_id', '=', user.id)]",
    ),
    (
        "resource_schedule_exception_rule_group_admin_modify",
        "resource.schedule.exception: admin modifies any",
        "[(1, '=', 1)]",
    ),
)


def migrate(cr, version):
    if not version:
        return

    for xmlid, name, domain in REPAIRS:
        cr.execute(
            """
            UPDATE ir_rule
            SET domain_force = %s, name = %s
            WHERE id = (
                SELECT res_id FROM ir_model_data
                WHERE module = 'resource' AND name = %s AND model = 'ir.rule'
            )
              AND (domain_force IS DISTINCT FROM %s OR name IS DISTINCT FROM %s)
            """,
            (domain, name, xmlid, domain, name),
        )
        if cr.rowcount:
            _logger.info("19.0.1.8: realigned ir.rule resource.%s with source.", xmlid)
