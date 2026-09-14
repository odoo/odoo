import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    _retire_experimental_gemini(api.Environment(cr, SUPERUSER_ID, {}))
    if table_exists(cr, "ai_model_fallback_rel"):
        _carry_fallback_relation(cr)


def _retire_experimental_gemini(env):
    experimental = env.ref(
        "gateway_ml.ai_model_gemini_2_0_flash_exp", raise_if_not_found=False
    )
    current = env.ref("gateway_ml.ai_model_gemini_3_5_flash_lite", raise_if_not_found=False)
    if not experimental or not current:
        return
    still_default = env["gateway.ml.provider"].search(
        [("default_model_id", "=", experimental.id)]
    )
    still_default.write({"default_model_id": current.id})
    if not env["gateway.ml.provider"].search_count(
        [("default_model_id", "=", experimental.id)]
    ):
        experimental.active = False
    _logger.info(
        "gateway_ml 19.0.1.18.0: %s provider(s) moved from gemini-2.0-flash-exp, an "
        "experimental id the catalog no longer runs, to gemini-3.5-flash-lite, the "
        "model vendor_catalog measured; the experimental row is archived, not "
        "deleted, and carries no price for the new one",
        len(still_default),
    )


def _carry_fallback_relation(cr):
    # Odoo never drops a code-defined Many2many's table; once its rows live in
    # gateway_ml_model_fallback the old table would only be a stale second chain.
    cr.execute(
        """
        INSERT INTO gateway_ml_model_fallback
               (model_id, fallback_id, sequence, create_date, write_date)
        SELECT r.model_id,
               r.fallback_id,
               row_number() OVER (
                   PARTITION BY r.model_id
                   ORDER BY e.sequence, e.name->>'en_US', p.id,
                            f.sequence, f.name->>'en_US', f.id
               ),
               now() AT TIME ZONE 'UTC',
               now() AT TIME ZONE 'UTC'
          FROM ai_model_fallback_rel r
          JOIN gateway_ml_model f ON f.id = r.fallback_id
          JOIN gateway_ml_provider p ON p.id = f.provider_id
          JOIN integration_service e ON e.id = p.endpoint_id
         WHERE r.model_id <> r.fallback_id
        ON CONFLICT (model_id, fallback_id) DO NOTHING
        """
    )
    carried = cr.rowcount
    cr.execute("DROP TABLE ai_model_fallback_rel")
    _logger.info(
        "gateway_ml 19.0.1.18.0: carried %s fallback hop(s) into gateway.ml.model.fallback in "
        "the order the Many2many used to run them (provider sequence and name, then "
        "model sequence and name); ai_model_fallback_rel is dropped, the relation it held now "
        "has a sequence",
        carried,
    )
