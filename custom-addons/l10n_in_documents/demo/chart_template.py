# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.tools.misc import file_open


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        if company and company.account_fiscal_country_id.code == 'IN':
            self._create_demo_data_documents(company)
        return super()._post_load_demo_data(company)

    @api.model
    def _create_demo_data_documents_folder(self, company):
        indian_companies = company or self.env['res.company'].search([('account_fiscal_country_id.code', '=', 'IN')])
        for indian_company in indian_companies:
            return self.env['documents.folder'].create({
                'name': 'Bills',
                'company_id': indian_company.id,
            })

    @api.model
    def _create_demo_data_documents(self, company=False):
        indian_companies = company or self.env['res.company'].search([('account_fiscal_country_id.code', '=', 'IN')])
        for indian_company in indian_companies:
            folder_id = self._create_demo_data_documents_folder(indian_company).id
            return self.env['documents.document'].create([
                {
                    'name': 'Invoice Ajio.pdf',
                    'folder_id': folder_id,
                    'raw': file_open(
                        'l10n_in_documents/static/demo/documents_vendor_bill_1.pdf', 'rb'
                    ).read(),
                },
                {
                    'name': 'Customer Invoice.pdf',
                    'folder_id': folder_id,
                    'raw': file_open(
                        'l10n_in_documents/static/demo/documents_vendor_bill_2.pdf', 'rb'
                    ).read(),
                },
                {
                    'name': 'Invoice Pushpak.pdf',
                    'folder_id': folder_id,
                    'raw': file_open(
                        'l10n_in_documents/static/demo/documents_vendor_bill_3.pdf', 'rb'
                    ).read(),
                },
                {
                    'name': 'Invoice Gajanand Trading.pdf',
                    'folder_id': folder_id,
                    'raw': file_open(
                        'l10n_in_documents/static/demo/documents_vendor_bill_4.pdf', 'rb'
                    ).read(),
                    },
                ])
