from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(model="account.depreciation.profile")
    def _get_account_depreciation_profile(self, template_code):
        return self._prepare_csv_vals(template_code, "account.depreciation.profile")
