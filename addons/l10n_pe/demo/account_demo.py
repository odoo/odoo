# -*- coding: utf-8 -*-

from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == "PE":
            move_data['demo_invoice_1']['l10n_latam_document_type_id'] = 'l10n_pe.document_type01'
            move_data['demo_invoice_1']['l10n_latam_document_number'] = 'FFI-000001'
            move_data['demo_invoice_2']['l10n_latam_document_type_id'] = 'l10n_pe.document_type01'
            move_data['demo_invoice_2']['l10n_latam_document_number'] = 'FFI-000002'
            move_data['demo_invoice_3']['l10n_latam_document_type_id'] = 'l10n_pe.document_type01'
            move_data['demo_invoice_3']['l10n_latam_document_number'] = 'FFI-000003'
            move_data['demo_invoice_followup']['l10n_latam_document_type_id'] = 'l10n_pe.document_type01'
            move_data['demo_invoice_followup']['l10n_latam_document_number'] = 'FFI-000004'
            move_data['demo_invoice_5']['l10n_latam_document_number'] = '1'
            move_data['demo_invoice_equipment_purchase']['l10n_latam_document_number'] = 'INV-000089'
        return move_data
