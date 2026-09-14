import logging

from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    if not table_exists(cr, "ai_provider_fallback_rel"):
        _logger.info(
            "gateway_ml 19.0.1.14.0: ai_provider_fallback_rel is already gone; "
            "no provider chain to carry"
        )
        return

    cr.execute(
        """
        INSERT INTO gateway_ml_model_fallback
               (model_id, fallback_id, sequence, create_date, write_date)
        SELECT p.default_model_id, f.default_model_id, 10,
               now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
          FROM ai_provider_fallback_rel r
          JOIN gateway_ml_provider p ON p.id = r.provider_id
          JOIN gateway_ml_provider f ON f.id = r.fallback_id
         WHERE p.default_model_id IS NOT NULL
           AND f.default_model_id IS NOT NULL
           AND p.default_model_id <> f.default_model_id
        ON CONFLICT (model_id, fallback_id) DO NOTHING
        """
    )
    carried = cr.rowcount

    cr.execute(
        """
        SELECT count(*)
          FROM ai_provider_fallback_rel r
          JOIN gateway_ml_provider p ON p.id = r.provider_id
          JOIN gateway_ml_provider f ON f.id = r.fallback_id
         WHERE p.default_model_id IS NULL
            OR f.default_model_id IS NULL
        """
    )
    unmapped = cr.fetchone()[0]

    if carried or unmapped:
        _logger.info(
            "gateway_ml 19.0.1.14.0: carried %s provider fallback hop(s) onto the "
            "two providers' default models. %s hop(s) named a provider with no "
            "default model and were dropped -- a hop that resolves to no model "
            "names nothing to run. ai_provider_fallback_rel is left in place and "
            "still holds what was configured: Odoo drops a relation table only "
            "for a manual field, so a code-defined Many2many keeps its rows",
            carried,
            unmapped,
        )
