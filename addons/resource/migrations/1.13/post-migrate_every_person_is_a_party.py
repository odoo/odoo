import logging

from odoo import SUPERUSER_ID, api
from odoo.db import schema

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE resource_resource r
           SET partner_id = u.partner_id
          FROM res_users u
         WHERE u.id = r.user_id
           AND r.resource_type = 'user'
           AND r.partner_id IS NULL
        """
    )
    _logger.info("%s human resources bound to their user's party", cr.rowcount)

    # hr binds an employee's resource to the employee's own party; a party made
    # here would be orphaned by that as soon as hr's migrations run.
    employee_resource_ids = set()
    if schema.table_exists(cr, "hr_employee"):
        cr.execute("SELECT resource_id FROM hr_employee")
        employee_resource_ids = {row[0] for row in cr.fetchall()}
    cr.execute(
        """
        SELECT id, name, tz
          FROM resource_resource
         WHERE resource_type = 'user'
           AND partner_id IS NULL
         ORDER BY id
        """
    )
    unbound = [row for row in cr.fetchall() if row[0] not in employee_resource_ids]
    if unbound:
        env = api.Environment(cr, SUPERUSER_ID, {})
        parties = env["res.partner"].create(
            [{"name": name, "tz": tz} for _id, name, tz in unbound]
        )
        env.flush_all()
        cr.execute(
            """
            UPDATE resource_resource r
               SET partner_id = bound.partner_id
              FROM unnest(%s::int[], %s::int[]) AS bound(resource_id, partner_id)
             WHERE r.id = bound.resource_id
            """,
            [[row[0] for row in unbound], parties.ids],
        )
    _logger.info("%s human resources given a party of their own", len(unbound))

    cr.execute(
        """
        UPDATE resource_resource r
           SET name = p.name
          FROM res_partner p
         WHERE p.id = r.partner_id
           AND p.name IS NOT NULL
           AND r.name IS DISTINCT FROM p.name
           AND NOT EXISTS (
               SELECT 1 FROM resource_resource other
                WHERE other.partner_id = r.partner_id
                  AND other.company_id IS NOT DISTINCT FROM r.company_id
                  AND other.resource_type = 'user'
                  AND other.id <> r.id)
     RETURNING r.id
        """
    )
    renamed = [row[0] for row in cr.fetchall()]
    _logger.info(
        "%s resources took their party's name again: %s", len(renamed), renamed
    )

    cr.execute(
        """
        SELECT partner_id, company_id, array_agg(id ORDER BY id)
          FROM resource_resource
         WHERE resource_type = 'user'
         GROUP BY partner_id, company_id
        HAVING count(*) > 1
        """
    )
    for partner_id, company_id, resource_ids in cr.fetchall():
        _logger.warning(
            "party %s holds human resources %s in company %s; one person is one "
            "resource per company, so the unique index waits on this",
            partner_id,
            resource_ids,
            company_id,
        )
