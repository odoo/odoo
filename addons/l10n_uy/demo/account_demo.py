# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        # Do not load generic demo data on these companies
        uy_demo_companies = (
            self.env.ref('l10n_uy.demo_company_uy', raise_if_not_found=False),
        )
        if self.env.company in uy_demo_companies:
            return []

        for model, data in super()._get_demo_data(company=company):
            yield model, data
