import logging

from odoo import SUPERUSER_ID, api
from odoo.fields import Command

_logger = logging.getLogger(__name__)

RULE_GROUPS = {
    "hr_gamification.hr_gamification_badge_base_user_owned_access": (
        "gamification.group_gamification_user",
    ),
    "hr_gamification.hr_gamification_badge_base_user_not_owned_access": (
        "gamification.group_gamification_user",
    ),
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for rule_xmlid, group_xmlids in RULE_GROUPS.items():
        rule = env.ref(rule_xmlid, raise_if_not_found=False)
        if not rule:
            _logger.warning("t24520: rule %s not found, skipped", rule_xmlid)
            continue
        if rule._name != "ir.rule":
            # base 1.97 turned the rule into ir.access rows, one per group; the
            # data file ships the app tier's rows under their own ids
            _logger.info("t24520: %s is an ir.access row, skipped", rule_xmlid)
            continue
        rule.groups = [Command.set([env.ref(x).id for x in group_xmlids])]
        _logger.info("t24520: rule %s re-pointed to %s", rule_xmlid, group_xmlids)
