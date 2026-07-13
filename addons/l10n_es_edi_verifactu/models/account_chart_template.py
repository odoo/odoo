from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_common', 'account.tax')
    def _get_es_verifactu_account_tax(self):
        return self._parse_csv('es_common', 'account.tax', module='l10n_es_edi_verifactu')
