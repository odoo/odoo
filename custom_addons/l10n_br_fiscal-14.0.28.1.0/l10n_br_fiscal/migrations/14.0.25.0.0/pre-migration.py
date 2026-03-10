# Copyright (C) 2025 - Felipe M Pereira - Engenere
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    query = """
        DELETE FROM ir_model_fields
            WHERE model = 'l10n_br_fiscal.document.mixin.fields'
    """
    openupgrade.logged_query(env.cr, query)
