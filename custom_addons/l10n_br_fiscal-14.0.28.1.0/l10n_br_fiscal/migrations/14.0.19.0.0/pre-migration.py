# Copyright 2023 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def delete_model(cr, model_name):
    openupgrade.logged_query(
        cr,
        """
        DELETE FROM ir_model_access
        WHERE model_id = (SELECT id FROM ir_model where model = '%s')
        """
        % model_name,
    )
    openupgrade.logged_query(
        cr, "DELETE FROM ir_model_fields WHERE model = '%s'" % model_name
    )
    openupgrade.logged_query(cr, "DELETE FROM ir_model WHERE model = '%s'" % model_name)


@openupgrade.migrate()
def migrate(env, version):
    delete_model(env.cr, "l10n_br_fiscal.mdfe")
    delete_model(env.cr, "l10n_br_fiscal.dfe_xml")
