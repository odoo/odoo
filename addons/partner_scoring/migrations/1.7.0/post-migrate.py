import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists

_logger = logging.getLogger(__name__)

# The engine is the scoring module now: a row names its scorecard.dimension
# record instead of a Selection value, and carries the group whose ceiling its
# max_points is. partner_scoring's own dimension is mapped here; a module that
# adds dimensions maps its own rows in its own migration, and the Selection
# column goes in the end-migration once every module has had its turn.
JOB_METHODS = {
    "_update_scores": "_score_refresh",
    "_delay_scores_recompute": "_delay_score_refresh",
    "_reclassify_tiers": "_score_reclassify",
}


def migrate(cr, version):
    if not version or not column_exists(cr, "partner_score_line", "dimension"):
        return
    cr.execute(
        """
        UPDATE partner_score_line l
           SET dimension_id = d.id,
               grouping_key = l.dimension || ':' || split_part(l.source_key, ':', 2)
          FROM scorecard_dimension d
          JOIN scorecard s ON s.id = d.scorecard_id
         WHERE s.res_model = 'res.partner'
           AND s.company_id IS NULL
           AND d.code = l.dimension
           AND l.dimension = 'partner_attr'
           AND l.dimension_id IS NULL
        """
    )
    _logger.info(
        "partner_scoring 1.7.0: %s partner_attr rows point at their dimension",
        cr.rowcount,
    )
    cr.execute(
        "UPDATE partner_score_line SET applicable = TRUE WHERE applicable IS NULL"
    )
    recompute_scores(cr)
    if table_exists(cr, "ir_job"):
        for old, new in JOB_METHODS.items():
            cr.execute(
                "UPDATE ir_job SET method_name = %s, channel = 'scoring.refresh' "
                "WHERE model_name = 'res.partner' AND method_name = %s",
                (new, old),
            )
        cr.execute(
            """
            UPDATE ir_job
               SET identity_key = replace(
                       replace(identity_key, 'partner_scoring.recompute:', 'scoring.refresh:res.partner:'),
                       'partner_scoring.reclassify:', 'scoring.reclassify:res.partner:')
             WHERE identity_key LIKE 'partner_scoring.%%'
            """
        )


def recompute_scores(cr):
    """Recompute every partner's score and tier from the rows mapped so far.

    The ORM filled the new stored score_max_points at load, before the rows
    carried their groups. Done here, again by each module that maps rows of its
    own, and once more by the end-migration: a module's version is written when
    its load commits, so an upgrade that aborts between here and the end stage
    is rerun without ever reaching the end-migration, and the recompute has to
    be somewhere a rerun does reach.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = env["res.partner"].with_context(active_test=False).search([])
    for name in ("score", "score_points", "score_max_points", "tier_id"):
        env.add_to_compute(partners._fields[name], partners)
    partners.flush_recordset()
    cr.execute("SELECT count(*) FROM res_partner WHERE tier_id IS NULL")
    _logger.info(
        "partner_scoring 1.7.0: scores recomputed for %s partners; %s carry no "
        "tier because nothing scored them",
        len(partners),
        cr.fetchone()[0],
    )
