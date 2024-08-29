# -*- coding: utf-8 -*-
from odoo.addons import account
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountChartTemplate(models.AbstractModel, account.AccountChartTemplate):

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if company.account_fiscal_country_id in self.env.ref('base.europe').country_ids:
            company._map_eu_taxes()
