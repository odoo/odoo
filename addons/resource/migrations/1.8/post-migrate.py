import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

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
        rewrite_converted_domain(cr, "resource", xmlid, domain, logger=_logger)
        cr.execute(
            """
            UPDATE ir_access a SET name = %s
              FROM ir_model_data d
             WHERE d.model = 'ir.access' AND d.res_id = a.id
               AND d.module = 'resource' AND d.name = %s
               AND a.name IS DISTINCT FROM %s
            """,
            (name, xmlid, name),
        )
