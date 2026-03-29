# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        if self == self.env.ref('l10n_it.l10n_it_chart_template_generic', raise_if_not_found=False):
            tax = self.env.ref(f'l10n_it.{company.id}_00eu', raise_if_not_found=False)
            if tax:
                tax.write({
                    'l10n_it_has_exoneration': True,
                    'l10n_it_kind_exoneration': 'N3.2',
                    'l10n_it_law_reference': 'Art. 41, DL n. 331/93',
                })
        return res
