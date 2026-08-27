# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_demo_data(self, chart_template):
        super()._post_load_demo_data(chart_template)
        if chart_template != 'pa':
            return
        # set the positions on the partners that use them so they are visible on the contact
        for partner_xmlid, fiscal_position_xmlid in (
            ('l10n_pa.partner_pa_demo_4', 'fp_foreign'),
            ('l10n_pa.partner_pa_demo_5', 'fp_zona_franca'),
        ):
            partner = self.env.ref(partner_xmlid, raise_if_not_found=False)
            fiscal_position = self.ref(fiscal_position_xmlid, raise_if_not_found=False)
            if partner and fiscal_position:
                partner.property_account_position_id = fiscal_position
