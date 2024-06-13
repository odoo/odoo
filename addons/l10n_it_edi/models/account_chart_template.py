# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        """
            Override normal default taxes, which are the ones with lowest sequence.
        """
        result = super()._post_load_data(template_code, company, template_data)
        if template_code == 'it':
            company.account_sale_tax_id = self.ref('22v')
            company.account_purchase_tax_id = self.ref('22am')
        return result

    @template('it', 'account.tax')
    def _get_it_account_tax(self):
        return {
            '00eu': {
                'l10n_it_has_exoneration': True,
                'l10n_it_kind_exoneration': 'N3.2',
                'l10n_it_law_reference': 'Art. 41, DL n. 331/93',
            }
        }
