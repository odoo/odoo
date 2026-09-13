import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    categories = env["approval.category"]
    for category in categories._unorder_group_categories():
        _logger.warning(
            "approval category %s (#%s) takes its approvers from a security group "
            "and no longer asks them one at a time in record order",
            category.name,
            category.id,
        )
    converted = categories._convert_every_category_to_steps()
    for category in converted["converted"]:
        _logger.info(
            "approval category %s (#%s) now routes by %s step(s)",
            category.name,
            category.id,
            len(category.step_ids),
        )
    result = categories._route_rules_of_step_categories_by_steps()
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
    census = env["approval.category"]._get_list_routing_census()
    for category in census["categories"]:
        _logger.warning(
            "approval category %s (#%s) still routes by its approver list: %s",
            category.name,
            category.id,
            " ".join(category._get_steps_conversion_blockers()),
        )
    _logger.info(
        "approval: %s undecided request(s) still route by an approver list, "
        "%s categor(ies) still do",
        len(census["requests"]),
        len(census["categories"]),
    )
