# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.models.chart_template import update_taxes_from_templates


def migrate(cr, version):
    cr.execute(
        r"""
        UPDATE ir_model_data
           SET name = name || '_producten'
         WHERE module = 'l10n_nl'
           AND model = 'account.tax'
           AND name ~ '^\d+_btw_X0$'
        """
    )

    update_taxes_from_templates(cr, 'l10n_nl.l10nnl_chart_template')
