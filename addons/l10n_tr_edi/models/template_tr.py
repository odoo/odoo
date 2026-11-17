from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("tr", "l10n_tr_edi.tax.code")
    def _get_tr_l10n_tr_edi_tax_code(self):
        return self._parse_csv("tr", "l10n_tr_edi.tax.code", module="l10n_tr_edi")
