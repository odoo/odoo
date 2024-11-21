from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo):
        res = super()._load(template_code, company, install_demo)
        if template_code == 'hu':
            company._l10n_hu_edi_configure_company()
        return res

    @template('hu', 'account.tax')
    def _get_hu_account_tax(self):
        data = self._parse_csv('hu', 'account.tax', module='l10n_hu_edi')
        return data
