import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or not column_exists(cr, "partner_score_line", "dimension"):
        return
    # Every installed module that ships a dimension has mapped its rows by now;
    # a row nobody claimed belongs to a dimension no installed module defines.
    cr.execute(
        "SELECT dimension, count(*) FROM partner_score_line "
        "WHERE dimension_id IS NULL GROUP BY dimension"
    )
    for code, count in cr.fetchall():
        _logger.warning(
            "partner_scoring 1.7.0: %s rows of dimension %r belong to no installed "
            "scorecard dimension and are dropped; the next refresh rebuilds them",
            count,
            code,
        )
    cr.execute("DELETE FROM partner_score_line WHERE dimension_id IS NULL")
    cr.execute("ALTER TABLE partner_score_line DROP COLUMN dimension")
    # The ORM filled the new stored score_max_points at load, before the rows
    # carried their group keys, and a tier now means a measurement was taken:
    # every partner's score and tier are recomputed from the mapped rows.
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
