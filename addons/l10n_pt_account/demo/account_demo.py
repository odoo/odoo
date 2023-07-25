# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company.account_fiscal_country_id.code == "PT":
            sale_journals = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)])
            sale_journals.l10n_pt_account_invoice_tax_authority_series_id = self.env.ref("l10n_pt_account.demo_invoice_series").id
            sale_journals.l10n_pt_account_refund_tax_authority_series_id = self.env.ref("l10n_pt_account.demo_refund_series").id
        return demo_data
