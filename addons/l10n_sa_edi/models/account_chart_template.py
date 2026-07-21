from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sa', 'account.tax')
    def _get_sa_edi_account_tax(self):
        return self._parse_csv('sa', 'account.tax', module='l10n_sa_edi')
