# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('it', 'account.tax')
    def _get_it_edi_doi_account_tax(self):
        tax_data = self._parse_csv('it', 'account.tax', module='l10n_it_edi_doi')
        self._deref_account_tags('it', tax_data)
        return tax_data

    @template('it', 'account.fiscal.position')
    def _get_it_edi_doi_account_fiscal_position(self):
        return self._parse_csv('it', 'account.fiscal.position', module='l10n_it_edi_doi')

    @template('it', 'res.company')
    def _get_it_edi_doi_res_company(self):
        return {
            self.env.company.id: {
                'l10n_it_edi_doi_tax_id': '00di',
                'l10n_it_edi_doi_fiscal_position_id': 'declaration_of_intent_fiscal_position',
            },
        }
