from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_common', 'account.tax')
    def _get_es_facturae_account_tax(self):
        taxes = self._parse_csv('es_common', 'account.tax', module='l10n_es_edi_facturae')
        # only return existing taxes
        taxes = {
            key: value
            for key, value in taxes.items()
            if self.env['account.chart.template'].ref(key, raise_if_not_found=False)
        }
        return taxes
