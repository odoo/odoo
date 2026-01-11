# -*- coding: utf-8 -*-
import logging

from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company in (
            self.env.ref('base.company_mono', raise_if_not_found=False),
            self.env.ref('base.company_exento', raise_if_not_found=False),
            self.env.ref('base.company_ri', raise_if_not_found=False),
        ):
            # Do not load generic demo data on these companies
            return {}

        if company.account_fiscal_country_id.code == "AR":
            demo_data = {
                'res.partner': demo_data.pop('res.partner', {}),
                **demo_data,
            }
            demo_data['res.partner'].setdefault('base.res_partner_2', {})
            demo_data['res.partner']['base.res_partner_2']['l10n_ar_afip_responsibility_type_id'] = 'l10n_ar.res_IVARI'
            demo_data['res.partner'].setdefault('base.res_partner_12', {})
            demo_data['res.partner']['base.res_partner_12']['l10n_ar_afip_responsibility_type_id'] = 'l10n_ar.res_IVARI'
        return demo_data

    @api.model
    def _get_demo_data_move(self, company=False):
        data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == "AR":
            data[self.company_xmlid('demo_invoice_8')]['l10n_latam_document_number'] = '1-1'
            data[self.company_xmlid('demo_invoice_equipment_purchase')]['l10n_latam_document_number'] = '1-2'
            data[self.company_xmlid('demo_move_auto_reconcile_3')]['l10n_latam_document_number'] = '1-3'
            data[self.company_xmlid('demo_move_auto_reconcile_4')]['l10n_latam_document_number'] = '1-4'
        return data

    def _post_load_demo_data(self, company=False):
        if company not in (
            self.env.ref('base.company_mono', raise_if_not_found=False),
            self.env.ref('base.company_exento', raise_if_not_found=False),
            self.env.ref('base.company_ri', raise_if_not_found=False),
        ):
            # Do not load generic demo data on these companies
            return super()._post_load_demo_data(company)
