# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


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
