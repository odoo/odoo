# -*- coding: utf-8 -*-

from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'EC':
            move_data[self.company_xmlid('demo_invoice_1')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_01'
            move_data[self.company_xmlid('demo_invoice_2')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_01'
            move_data[self.company_xmlid('demo_invoice_3')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_01'
            move_data[self.company_xmlid('demo_invoice_followup')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_01'
            move_data[self.company_xmlid('demo_invoice_8')]['l10n_latam_document_number'] = '001-001-00001'
            move_data[self.company_xmlid('demo_invoice_equipment_purchase')]['l10n_latam_document_number'] = '001-001-00002'
            move_data[self.company_xmlid('demo_move_auto_reconcile_1')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_04'
            move_data[self.company_xmlid('demo_move_auto_reconcile_2')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_04'
            move_data[self.company_xmlid('demo_move_auto_reconcile_3')]['l10n_latam_document_number'] = '001-001-00003'
            move_data[self.company_xmlid('demo_move_auto_reconcile_4')]['l10n_latam_document_number'] = '001-001-00004'
            move_data[self.company_xmlid('demo_move_auto_reconcile_5')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_04'
            move_data[self.company_xmlid('demo_move_auto_reconcile_6')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_04'
            move_data[self.company_xmlid('demo_move_auto_reconcile_7')]['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_04'
        return move_data
