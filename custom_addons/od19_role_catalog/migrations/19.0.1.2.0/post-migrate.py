"""Restore the missing CEO expense group on ``role_expense_ceo_approver``.

``od19_role_catalog`` seeds every role with ``noupdate="1"`` so administrators
can retune them in the UI without the next upgrade overwriting their changes.
The CEO expense approver role was seeded while ``group_od19_expense_ceo_approver``
(owned by ``od19_hr_expense_thai``) did not exist yet, so its ``implied_ids``
froze incomplete (only ``hr_expense.group_hr_expense_user``).

``res.users.role`` inherits ``res.groups`` through ``group_id``, so a role's
``implied_ids`` live on the m2m relation ``res_groups_implied_rel``
(``gid`` = the role's own group).  This one-shot migration adds the missing
link once; it never removes anything, so administrator tuning is preserved.
"""

import logging

_logger = logging.getLogger(__name__)

ROLE_MODULE = "od19_role_catalog"
ROLE_XMLID = "role_expense_ceo_approver"
GROUP_MODULE = "od19_hr_expense_thai"
GROUP_XMLID = "group_od19_expense_ceo_approver"


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT rur.group_id
          FROM ir_model_data AS imd
          JOIN res_users_role AS rur ON rur.id = imd.res_id
         WHERE imd.module = %s
           AND imd.name = %s
           AND imd.model = 'res.users.role'
        """,
        (ROLE_MODULE, ROLE_XMLID),
    )
    role_row = cr.fetchone()
    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = %s AND name = %s AND model = 'res.groups'
        """,
        (GROUP_MODULE, GROUP_XMLID),
    )
    group_row = cr.fetchone()
    if not role_row or not group_row:
        _logger.info(
            "od19_role_catalog: CEO expense role or group not found, skip relink"
        )
        return
    cr.execute(
        """
        INSERT INTO res_groups_implied_rel (gid, hid)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (role_row[0], group_row[0]),
    )
    _logger.info(
        "od19_role_catalog: linked CEO expense group to role (group %s -> %s)",
        role_row[0],
        group_row[0],
    )
