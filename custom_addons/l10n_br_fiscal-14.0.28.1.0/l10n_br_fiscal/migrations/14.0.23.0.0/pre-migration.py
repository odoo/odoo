# Copyright (C) 2024 - TODAY - Raphaël Valyi - Akretion <raphael.valyi@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

to_install = "l10n_br_fiscal_edi"


def install_new_modules(cr):
    sql = """
    UPDATE ir_module_module
    SET state='to install'
    WHERE name = '{}' AND state='uninstalled'
    """.format(
        to_install,
    )
    openupgrade.logged_query(cr, sql)


@openupgrade.migrate()
def migrate(env, version):
    install_new_modules(env.cr)
    query = """
        DELETE FROM ir_model_fields
            WHERE model = 'l10n_br_fiscal.document.electronic'
    """
    openupgrade.logged_query(env.cr, query)
