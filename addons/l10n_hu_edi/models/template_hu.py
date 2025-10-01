from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo, force_create=True):
        res = super()._load(template_code, company, install_demo, force_create)
        if template_code == 'hu':
            company._l10n_hu_edi_configure_company()
        return res

    @template('hu', 'account.tax')
    def _get_hu_account_tax(self):
        data = self._parse_csv('hu', 'account.tax', module='l10n_hu_edi')
        return data

    @template('hu', 'account.cash.rounding')
    def _get_hu_account_rounding(self):
        return {
            'cash_rounding_1_huf': {
                'name': "Rounding to 1.00",
                'name@hu': "Kerekítés 1.00-ra",
                'rounding': 1.0,
                'strategy': 'add_invoice_line'
            }
        }
