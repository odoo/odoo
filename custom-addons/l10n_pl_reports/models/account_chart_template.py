# -*- coding: utf-8 -*-

from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pl', 'res.company')
    def _get_pl_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'chart14000200',
            }
        }
