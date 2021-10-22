# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', 'res.company')
    def _get_in_res_company(self):
        company_data = super()._get_in_res_company()
        company_data[self.env.company.id].update({
            'account_opening_date': fields.Date.context_today(self).replace(month=4, day=1),
            'fiscalyear_last_month': '3',
        })
        return company_data
