from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(model="account.asset")
    def _get_account_asset(self, template_code):
        return {
            xmlid: {
                "state": "model",
                **vals,
            }
            for xmlid, vals in self._prepare_csv_vals(
                template_code, "account.asset"
            ).items()
        }
