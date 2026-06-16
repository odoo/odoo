from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sa', 'account.tax')
    def _get_sa_edi_account_tax(self):
        tax_data = self._parse_csv('sa', 'account.tax', module='l10n_sa_edi')
        return {
            xmlid: vals
            for xmlid, vals in tax_data.items()
            if self.env.ref(xmlid, raise_if_not_found=False)
        }
