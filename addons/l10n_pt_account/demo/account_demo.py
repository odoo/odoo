# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company.account_fiscal_country_id.code == "PT":
            sale_journals = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)])
            demo_series = self.env["l10n_pt_account.tax.authority.series"].create({
                'code': 'DEMOSERIES',
                'end_date': '2023-12-31',
            })
            sale_journals.l10n_pt_account_tax_authority_series_id = demo_series
        return demo_data
