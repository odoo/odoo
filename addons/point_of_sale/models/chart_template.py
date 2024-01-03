# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo):
        """Remove the payment methods that are created for the company and unset journals before installing the chart of accounts.

        Keeping these existing pos.payment.method records and pos.config journals interferes with the installation of chart of accounts
        because pos.payment.method model has fields linked to account.journal and account.account records that are
        deleted during the loading of chart of accounts.
        """
        reload_template = template_code == company.chart_template
        if not reload_template:
            self.env['pos.payment.method'].with_context(active_test=False).search(self.env['pos.payment.method']._check_company_domain(company)).unlink()
            self.env["pos.config"].with_context(active_test=False).search(self.env['pos.config']._check_company_domain(company)).write({
                'journal_id': False,
                'invoice_journal_id': False,
            })
        result = super()._load(template_code, company, install_demo)
        self.env['pos.config'].post_install_pos_localisation(companies=company)
        return result
