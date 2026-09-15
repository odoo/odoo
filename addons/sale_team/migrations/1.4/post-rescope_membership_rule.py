import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT d.res_id
          FROM ir_model_data d
         WHERE d.module = 'sale_team'
           AND d.name = 'crm_team_member_rule_personal'
           AND d.model = 'ir.rule'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    rule_id = row[0]

    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'base'
           AND name = 'group_user'
           AND model = 'res.groups'
        """
    )
    row = cr.fetchone()
    if not row:
        _logger.warning(
            "sale_team: base.group_user is missing, leaving "
            "crm_team_member_rule_personal on its recorded groups"
        )
        return
    group_id = row[0]

    cr.execute(
        "SELECT group_id FROM rule_group_rel WHERE rule_group_id = %s", (rule_id,)
    )
    linked = {gid for [gid] in cr.fetchall()}

    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'sale_team'
           AND name = 'group_sale_salesman'
           AND model = 'res.groups'
        """
    )
    row = cr.fetchone()
    salesman_id = row[0] if row else None

    untouched = salesman_id is not None and linked == {salesman_id}
    if untouched:
        cr.execute("DELETE FROM rule_group_rel WHERE rule_group_id = %s", (rule_id,))
    elif group_id in linked:
        return

    cr.execute(
        """
        INSERT INTO rule_group_rel (rule_group_id, group_id)
             VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (rule_id, group_id),
    )
    _logger.info(
        "sale_team: crm_team_member_rule_personal now carries base.group_user "
        "(%s); memberships are scoped for every internal user, not only Sales ones",
        "replacing the recorded group" if untouched else "added beside local edits",
    )
