from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ge", "account.tax.group")
    def _get_ge_withholding_account_tax_group(self):
        return self._parse_csv("ge", "account.tax.group", module="l10n_ge_withholding")

    @template("ge", "account.tax")
    def _get_ge_withholding_account_tax(self):
        tax_data = self._parse_csv("ge", "account.tax", module="l10n_ge_withholding")
        self._deref_account_tags("ge", tax_data)
        return tax_data
