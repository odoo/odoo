import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    result = env["approval.category"]._route_rules_of_step_categories_by_steps()
    for rule in result["added"]:
        _logger.info(
            "approval rule %s (#%s) of %s now applies a step of its approvers",
            rule.name,
            rule.id,
            rule.category_id.name,
        )
    for rule in result["archived"]:
        _logger.info(
            "approval rule %s (#%s) of %s archived: a category routed by steps "
            "never replaced its approvers by it",
            rule.name,
            rule.id,
            rule.category_id.name,
        )
