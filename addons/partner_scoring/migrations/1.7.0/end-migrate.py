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
    # Once more, after every module mapped its rows and the column is gone.
    # Duplicated from post-migrate.py, which says why it runs there too: a
    # migration script is loaded by path and cannot import its sibling.
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = env["res.partner"].with_context(active_test=False).search([])
    for name in ("score", "score_points", "score_max_points", "tier_id"):
        env.add_to_compute(partners._fields[name], partners)
    partners.flush_recordset()
    _logger.info(
        "partner_scoring 1.7.0: %s partners recomputed at the end", len(partners)
    )
