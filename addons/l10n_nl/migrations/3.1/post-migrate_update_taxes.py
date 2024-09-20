# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.models.chart_template import update_taxes_from_templates
from odoo.addons.base.maintenance.migrations import util


def migrate(cr, version):
    cr.execute(
        r"""
        SELECT name
          FROM ir_model_data
         WHERE module = 'l10n_nl'
           AND model = 'account.tax'
           AND name ~* '\d+_btw_x0$'
        """
    )
    for record in cr.fetchall():
        util.rename_xmlid(cr, "l10n_nl.{}".format(record[0]), "l10n_nl.{}_producten".format(record[0]))
    update_taxes_from_templates(cr, 'l10n_nl.l10nnl_chart_template')
