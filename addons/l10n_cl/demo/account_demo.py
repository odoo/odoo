# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self):
        yield ('res.partner', {
            'base.res_partner_12': {
                'l10n_cl_sii_taxpayer_type': '4',
            },
            'base.res_partner_2': {
                'l10n_cl_sii_taxpayer_type': '4',
            },
        })
        yield ('l10n_latam.document.type', {
            'l10n_cl.dc_fe_dte': {'active': True},
        })
        for model, data in super()._get_demo_data():
            yield model, data

    @api.model
    def _get_demo_data_move(self):
        ref = self.env.ref
        cid = self.env.company.id
        model, data = super()._get_demo_data_move()
        if self.env.company.country_code == "CL":
            foreign = ref('l10n_cl.dc_fe_dte').id
            self.env['account.journal'].search([
                ('type', '=', 'purchase'),
                ('company_id', '=', self.env.company.id),
            ]).l10n_latam_use_documents = False
            data[f'{cid}_demo_invoice_1']['l10n_latam_document_type_id'] = foreign
            data[f'{cid}_demo_invoice_2']['l10n_latam_document_type_id'] = foreign
            data[f'{cid}_demo_invoice_3']['l10n_latam_document_type_id'] = foreign
            data[f'{cid}_demo_invoice_followup']['l10n_latam_document_type_id'] = foreign
        return model, data
