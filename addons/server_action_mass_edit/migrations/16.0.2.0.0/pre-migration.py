# Copyright (C) 2022 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    cr = env.cr

    if not openupgrade.table_exists(cr, "mass_editing_line"):
        return

    openupgrade.rename_models(
        cr, [("mass.editing.line", "ir.actions.server.mass.edit.line")]
    )
    openupgrade.rename_tables(
        cr, [("mass_editing_line", "ir_actions_server_mass_edit_line")]
    )
