# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ng', 'account.account')
    def _get_ng_account_account(self):
        """ Nigerian companies are fine with using the generic COA
        but we need to add Nigeria-specific taxes and a tax report
        """
        return {
            **{f'l10n_ng_{k}': v for k, v in self._parse_csv('generic_coa', 'account.account').items()},
            'l10n_ng_withholding': {
                'name': _("Withholding Tax on Purchases"),
                'code': '252001',
                'account_type': 'liability_current',
                'reconcile': False,
            },
            'l10n_ng_withholding_transitional': {
                'name': _("Withholding Tax on Purchases - Transition Account"),
                'code': '252002',
                'account_type': 'liability_current',
                'reconcile': True,
            },
            'l10n_ng_withholding_payable': {
                'name': _("Withholding Tax Payable"),
                'code': '252003',
                'account_type': 'liability_payable',
                'reconcile': True,
                'non_trade': True,
            },
        }

    @template('ng')
    def _get_ng_template_data(self):
        """ Copies the generic CoA template data.
        Changes to it will be reflected here as well.
        We remove the name and country to use the default values,
        whereas the generic CoA has to override these.
        """
        res = self._get_generic_coa_template_data()
        return {k: f'l10n_ng_{v}' for k, v in res.items() if k not in ('name', 'country')}

    @template('ng', 'res.company')
    def _get_ng_res_company(self):
        res_company_data = self._get_generic_coa_res_company()[self.env.company.id]
        res_company_data['account_fiscal_country_id'] = 'base.ng'

        for field, value in res_company_data.items():
            if 'account_id' in field:
                res_company_data[field] = f'l10n_ng_{value}'
        return {self.env.company.id: res_company_data}
