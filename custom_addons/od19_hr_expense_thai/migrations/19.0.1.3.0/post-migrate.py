"""Re-link the CEO reviewer group on the seeded ``tier.definition``.

The three ``tier.definition`` records of ``hr.expense`` are seeded with
``noupdate="1"``.  The CEO definition was introduced in one release and the CEO
approver group (``group_od19_expense_ceo_approver``) in a later one, so the
``reviewer_group_id`` of the CEO definition was written as ``NULL`` while the
group did not exist yet.  Because the row is ``noupdate``, Odoo never refreshed
it afterwards and the third approval level ended up without a reviewer.

``ir_model_data.noupdate`` is only set when the XMLID row is first inserted
(``_build_update_xmlids_query`` never updates the column) and ``_load_records``
skips the write when the flag is set, so changing the XML alone cannot repair an
already-upgraded database.  This one-shot migration applies the intended link.
"""

import logging

_logger = logging.getLogger(__name__)

MODULE = "od19_hr_expense_thai"
TIER_XMLID = "tier_definition_hr_expense_ceo"
GROUP_XMLID = "group_od19_expense_ceo_approver"


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE tier_definition AS td
           SET reviewer_group_id = grp.res_id
          FROM ir_model_data AS def, ir_model_data AS grp
         WHERE def.module = %s
           AND def.name = %s
           AND def.model = 'tier.definition'
           AND td.id = def.res_id
           AND grp.module = %s
           AND grp.name = %s
           AND grp.model = 'res.groups'
        """,
        (MODULE, TIER_XMLID, MODULE, GROUP_XMLID),
    )
    _logger.info(
        "od19_hr_expense_thai: linked CEO reviewer group on %s tier definition(s)",
        cr.rowcount,
    )
