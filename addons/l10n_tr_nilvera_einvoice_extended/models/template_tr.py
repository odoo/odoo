# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("tr", "account.tax")
    def _get_tr_withholding_account_tax(self):
        additional = self._parse_csv(
            "tr", "account.tax", module="l10n_tr_nilvera_einvoice_extended"
        )
        self._deref_account_tags("tr", additional)
        return additional
