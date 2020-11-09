# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load_chart_template(self):
        # OVERRIDE
        # Remove the payment methods that are created for the company before installing the chart of accounts.
        # Keeping these existing pos.payment.method records interferes with the installation of chart of accounts
        # because pos.payment.method model has fields linked to account.journal and account.account records that are
        # deleted during the loading of chart of accounts.
        self.env['pos.payment.method'].search([('company_id', '=', self.env.company.id)]).unlink()
        res = super()._load_chart_template()
        self.env['pos.config'].post_install_pos_localisation(companies=self.env.company)
        return res
