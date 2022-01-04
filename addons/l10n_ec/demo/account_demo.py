# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self):
        ref = self.env.ref
        cid = self.env.company.id
        model, data = super()._get_demo_data_move()
        if self.env.company.country_id.code == 'EC':
            document_type = ref('l10n_ec.ec_dt_18', False) and ref('l10n_ec.ec_dt_18').id or False
            data[f'{cid}_demo_invoice_1']['l10n_latam_document_type_id'] = document_type
            data[f'{cid}_demo_invoice_2']['l10n_latam_document_type_id'] = document_type
            data[f'{cid}_demo_invoice_3']['l10n_latam_document_type_id'] = document_type
            data[f'{cid}_demo_invoice_followup']['l10n_latam_document_type_id'] = document_type
            data[f'{cid}_demo_invoice_5']['l10n_latam_document_number'] = '001-001-00001'
            data[f'{cid}_demo_invoice_equipment_purchase']['l10n_latam_document_number'] = '001-001-00002'
        return model, data
