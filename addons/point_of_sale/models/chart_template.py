# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code=False, company=False, install_demo=True):
        """Remove the payment methods that are created for the company before installing the chart of accounts.

        Keeping these existing pos.payment.method records interferes with the installation of chart of accounts
        because pos.payment.method model has fields linked to account.journal and account.account records that are
        deleted during the loading of chart of accounts.
        """
        self.env['pos.payment.method'].search([('company_id', '=', company.id)]).unlink()
        result = super()._load(template_code, company, install_demo)
        self.env['pos.config'].post_install_pos_localisation(companies=company)
        return result
