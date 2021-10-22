# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'EC':
            move_data['demo_invoice_1']['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_18'
            move_data['demo_invoice_2']['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_18'
            move_data['demo_invoice_3']['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_18'
            move_data['demo_invoice_followup']['l10n_latam_document_type_id'] = 'l10n_ec.ec_dt_18'
            move_data['demo_invoice_5']['l10n_latam_document_number'] = '001-001-00001'
            move_data['demo_invoice_equipment_purchase']['l10n_latam_document_number'] = '001-001-00002'
        return move_data
