# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pt', 'account.tax')
    def _get_pt_certification_account_tax(self):
        return self._parse_csv('pt', 'account.tax', module='l10n_pt_certification')

    @template('pt', 'account.tax.group')
    def _get_pt_certification_account_tax_group(self):
        return self._parse_csv('pt', 'account.tax.group', module='l10n_pt_certification')

    def _l10n_pt_load_certification_tax_data(self, company):
        """
        Add to the taxes and tax groups of ``company``'s PT chart what the certification defines on
        them (VAT exemption reasons, tax regions and categories), for a chart loaded before this module.
        """
        template = self.with_company(company)
        template._load_data({
            'account.tax': template._get_pt_certification_account_tax(),
            'account.tax.group': template._get_pt_certification_account_tax_group(),
        })
