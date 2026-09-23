import logging

from odoo import SUPERUSER_ID, api
from odoo.fields import Command

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Re-point the root menu onto the app group.

    :param cr: database cursor
    :param version: module version being upgraded from
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # the rules follow the app groups through base 1.97, which releases a
    # noupdate row the data file ships for another group to that file.

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

    # No registry.clear_cache() call: ir.ui.menu.write clears it itself.
