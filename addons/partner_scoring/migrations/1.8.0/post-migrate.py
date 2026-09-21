import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Growth outlook was captured on 446 production customers and weighed nothing.
# The seeds are noupdate, so the three values take their weight here when they
# still carry none, and every scored partner is rescored inline: a catalog
# notification queues a job, and during an upgrade the registry is not ready.
WEIGHTS = {
    "partner_attribute_value_growth_expansion": 10.0,
    "partner_attribute_value_growth_stable": 6.0,
    "partner_attribute_value_growth_contraction": 2.0,
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    weighted = 0
    for xml_id, weight in WEIGHTS.items():
        value = env.ref(f"partner_scoring.{xml_id}", raise_if_not_found=False)
        if value is not None and not value.score_value:
            cr.execute(
                "UPDATE res_partner_attribute_value SET score_value = %s WHERE id = %s",
                (weight, value.id),
            )
            weighted += 1
    if not weighted:
        return
    env.invalidate_all()
    partners = (
        env["res.partner"]
        .with_context(active_test=False)
        .search([("score_line_ids", "!=", False)])
    )
    partners._score_refresh()
    _logger.info(
        "partner_scoring 1.8.0: Growth outlook weighted (%s values), %s scored "
        "partners rescored",
        weighted,
        len(partners),
    )
