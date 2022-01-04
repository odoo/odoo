# -*- coding: utf-8 -*-

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self):
        cid = self.env.company.id
        model, data = super()._get_demo_data_move()
        if self.env.company.country_code == "PE":
            document_type = self.env.ref('l10n_pe.document_type01')
            data[f'{cid}_demo_invoice_1']['l10n_latam_document_type_id'] = document_type.id
            data[f'{cid}_demo_invoice_1']['l10n_latam_document_number'] = 'FFI-000001'
            data[f'{cid}_demo_invoice_2']['l10n_latam_document_type_id'] = document_type.id
            data[f'{cid}_demo_invoice_2']['l10n_latam_document_number'] = 'FFI-000002'
            data[f'{cid}_demo_invoice_3']['l10n_latam_document_type_id'] = document_type.id
            data[f'{cid}_demo_invoice_3']['l10n_latam_document_number'] = 'FFI-000003'
            data[f'{cid}_demo_invoice_followup']['l10n_latam_document_type_id'] = document_type.id
            data[f'{cid}_demo_invoice_followup']['l10n_latam_document_number'] = 'FFI-000004'
            data[f'{cid}_demo_invoice_5']['l10n_latam_document_number'] = '1'
            data[f'{cid}_demo_invoice_equipment_purchase']['l10n_latam_document_number'] = 'INV-000089'
        return model, data
