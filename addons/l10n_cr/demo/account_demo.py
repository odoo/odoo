from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_demo_data(self, chart_template):
        super()._post_load_demo_data(chart_template)
        if chart_template != 'cr':
            return
        partner = self.env.ref('l10n_cr.demo_partner_zona_franca', raise_if_not_found=False)
        fiscal_position = self.ref('fiscal_position_cr_zona_franca', raise_if_not_found=False)
        if partner and fiscal_position:
            partner.property_account_position_id = fiscal_position
