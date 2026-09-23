from odoo.db.schema import table_exists
from odoo.tools import SQL
from odoo.tools.module_data import (
    rename_field,
    rename_in_stored_expressions,
    rename_model,
)

# partner.profile named a band and the credit dossier names a file; the band is
# a tier now. The partner's score fields take the names every scored model will
# share, and the audit line keys on its subject rather than on "the partner".
PARTNER_FIELDS = {
    "partner_profile_id": "tier_id",
    "score_pct": "score",
    "date_last_score_update": "score_date",
    "score_max_possible": "score_max_points",
}
LINE_FIELDS = {"partner_id": "subject_id"}
METHODS = {
    "_update_profile_scores": "_update_scores",
    "_delay_profile_scores_recompute": "_delay_scores_recompute",
    "_reclassify_profile_bands": "_reclassify_tiers",
}
XMLID_MODELS = (
    "ir.ui.view",
    "ir.actions.act_window",
    "ir.access",
    "ir.ui.menu",
)


def migrate(cr, version):
    if not version:
        return
    if table_exists(cr, "partner_profile") and not table_exists(cr, "partner_tier"):
        rename_model(cr, "partner.profile", "partner.tier")
    cr.execute(
        """
        UPDATE ir_model_data d
           SET name = replace(d.name, 'partner_profile', 'partner_tier')
         WHERE d.module = 'partner_scoring'
           AND d.model = ANY(%s)
           AND d.name LIKE '%%partner\\_profile%%'
           AND NOT EXISTS (
                SELECT 1 FROM ir_model_data e
                 WHERE e.module = d.module
                   AND e.name = replace(d.name, 'partner_profile', 'partner_tier')
           )
        """,
        [list(XMLID_MODELS)],
    )
    for old, new in PARTNER_FIELDS.items():
        rename_field(cr, "res.partner", old, new)
        rename_in_stored_expressions(cr, old, new, model="res.partner")
    for old, new in LINE_FIELDS.items():
        rename_field(cr, "partner.score.line", old, new)
        rename_in_stored_expressions(cr, old, new, model="partner.score.line")
    # A queued rescore names its method; a pending wave must land on the new one.
    if table_exists(cr, "ir_job"):
        for old, new in METHODS.items():
            cr.execute(
                SQL(
                    "UPDATE ir_job SET method_name = %s "
                    "WHERE model_name = 'res.partner' AND method_name = %s",
                    new,
                    old,
                )
            )
