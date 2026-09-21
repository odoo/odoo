import logging

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
