from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("tr", "account.tax")
    def _get_tr_withholding_account_tax(self):
        additional = self._parse_csv("tr", "account.tax", module="l10n_tr_nilvera_einvoice_extended")
        self._deref_account_tags("tr", additional)
        return additional

    @template("tr", "l10n_tr_nilvera_einvoice_extended.account.tax.code")
    def _get_tr_withholding_account_tax_code(self):
        return self._parse_csv("tr", "l10n_tr_nilvera_einvoice_extended.account.tax.code", module="l10n_tr_nilvera_einvoice_extended")
