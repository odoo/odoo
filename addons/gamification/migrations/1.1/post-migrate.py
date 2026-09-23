import logging

from odoo import SUPERUSER_ID, api
from odoo.fields import Command

_logger = logging.getLogger(__name__)

# ir.rule xml_id -> the COMPLETE set of groups the rule must end up with.
# Declarative on purpose: writing the whole target set with Command.set makes the
# script idempotent whatever the current state is, instead of diffing link/unlink
# against groups the database may or may not still hold.
# To revert: invert this map back to base.group_user / base.group_erp_manager and
# re-link base.group_no_one on the root menu.
RULE_GROUPS = {
    "gamification.goal_user_visibility": (
        "gamification.group_gamification_user",
        "base.group_portal",  # kept: the portal audience is not ours to re-point
    ),
    "gamification.goal_gamification_manager_visibility": (
        "gamification.group_gamification_manager",
    ),
    # gamification.streak_user_write was removed in 1.2: it granted nothing,
    # because ir.model.access.csv gives employees read-only access to
    # gamification.streak and a record rule cannot widen an ACL.  The loop below
    # already skips a rule it cannot resolve, so an older database that still
    # carries the row is handled either way.
    "gamification.kudos_user_write": ("gamification.group_gamification_user",),
    "gamification.mentorship_own_only": ("gamification.group_gamification_user",),
    "gamification.mentorship_manager_rule": (
        "gamification.group_gamification_manager",
    ),
    "gamification.activity_visibility": ("gamification.group_gamification_user",),
}


def migrate(cr, version):
    """Re-point the noupdate record rules and the root menu onto the app groups.

    :param cr: database cursor
    :param version: module version being upgraded from
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # security/gamification_security.xml opens with <odoo noupdate="1">, so the
    # group change in the data file never reaches an already-loaded database on -u
    # (ir_model_data.py:529 excludes noupdate rows from both cleanup and
    # re-assertion). Without this, the old base.* groups stay in force.
    for rule_xmlid, group_xmlids in RULE_GROUPS.items():
        rule = env.ref(rule_xmlid, raise_if_not_found=False)
        if not rule:
            # A hand-deleted rule is not an upgrade failure: skip it and say so.
            _logger.warning("t24520: rule %s not found, skipped", rule_xmlid)
            continue
        if rule._name != "ir.rule":
            # base 1.97 turned the rule into ir.access rows, one per group; the
            # data file ships the app tier's rows under their own ids
            _logger.info("t24520: %s is an ir.access row, skipped", rule_xmlid)
            continue
        # Hard ref for the groups: they are loaded by the same -u that runs this
        # script, so a missing one means a broken upgrade and must fail loudly.
        group_ids = [env.ref(xmlid).id for xmlid in group_xmlids]
        rule.groups = [Command.set(group_ids)]
        _logger.info("t24520: rule %s re-pointed to %s", rule_xmlid, group_xmlids)

    # <menuitem groups="..."> emits Command.link (tools/convert.py:347), which is
    # ADDITIVE: on an existing database the root would keep its base.group_no_one
    # link next to the new group, and the tree would stay dev-mode-only for
    # everyone else. Set the full target set instead.
    root_menu = env.ref("gamification.gamification_menu", raise_if_not_found=False)
    if not root_menu:
        _logger.warning("t24520: root menu not found, skipped")
        return
    app_group = env.ref("gamification.group_gamification_user")
    root_menu.group_ids = [Command.set([app_group.id])]
    _logger.info("t24520: root menu groups reset to %s", app_group.name)

    # No registry.clear_cache() call: ir.rule.write (ir_rule.py:214-217) and
    # ir.ui.menu.write (ir_ui_menu.py:230-232) both clear it themselves.
