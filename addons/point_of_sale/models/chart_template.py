# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _create_bank_journals(self, company, acc_template_ref):
        """
        Add the payment journals to the existing pos config
        """
        journals = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)
        self.env['pos.config'].assign_payment_journals(companies=company)
        return journals

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self).generate_journals(acc_template_ref, company, journals_dict)
        self.env['pos.config'].generate_pos_journal(companies=company)
        return res

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """Remove the payment methods that are created for the company before installing the chart of accounts.

        Keeping these existing pos.payment.method records interferes with the installation of chart of accounts
        because pos.payment.method model has fields linked to account.journal and account.account records that are
        deleted during the loading of chart of accounts.
        """
        self.env['pos.payment.method'].search([('company_id', '=', company.id)]).unlink()
        return super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
