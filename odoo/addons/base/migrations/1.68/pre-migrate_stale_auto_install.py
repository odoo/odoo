import logging

from odoo.modules.module import get_module_names

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    on_disk = set(get_module_names())
    cr.execute(
        """
        SELECT name, state FROM ir_module_module
         WHERE auto_install AND state != 'installed'
        """
    )
    stale = [name for name, _state in cr.fetchall() if name not in on_disk]
    if not stale:
        return
    # A module this fork deleted keeps its row, and the row keeps auto_install.
    # The loader marks such a module `to install` the day every dependency of it
    # happens to be installed, then cannot supply it, and the upgrade ends
    # "inconsistent ... some dependencies may be missing" naming a module nobody
    # can install. document_fleet reached that state through fleet and document.
    # Clearing the flag is self-healing: update_list rewrites it from the
    # manifest for any module that is actually present.
    cr.execute(
        """
        UPDATE ir_module_module
           SET auto_install = FALSE,
               state = CASE WHEN state = 'to install' THEN 'uninstalled' ELSE state END
         WHERE name = ANY(%s)
        """,
        [stale],
    )
    _logger.info(
        "cleared auto_install on %s module row(s) with no module on the addons "
        "path: %s",
        len(stale),
        ", ".join(sorted(stale)),
    )
