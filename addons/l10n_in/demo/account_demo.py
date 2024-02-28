# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self):
        company = self.env.company
        if company.account_fiscal_country_id.code == "IN":
            if company.state_id.country_id.code != "IN":
                company.state_id = self.env.ref("base.state_in_gj")
            if company.country_id.code != "IN":
                company.country_id = self.env.ref("base.in")
        return super()._get_demo_data()
