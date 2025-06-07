# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        ref = self.env.ref
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == "CL":
            foreign_invoice = ref('l10n_cl.dc_fe_dte').id
            foreign_credit_note = ref('l10n_cl.dc_ncex_dte').id
            self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'purchase'),
            ]).l10n_latam_use_documents = False
            move_data['demo_invoice_1']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_invoice_2']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_invoice_3']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_invoice_followup']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_move_auto_reconcile_1']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_2']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_5']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_6']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_7']['l10n_latam_document_type_id'] = foreign_credit_note
        return move_data
