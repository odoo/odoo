# -*- coding: utf-8 -*-
import logging

from odoo import api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company in (
            self.env.ref('l10n_ar.company_mono', raise_if_not_found=False),
            self.env.ref('l10n_ar.company_exento', raise_if_not_found=False),
            self.env.ref('l10n_ar.company_ri', raise_if_not_found=False),
        ):
            # Do not load generic demo data on these companies
            return {}

        if company.account_fiscal_country_id.code == "AR":
            demo_data.setdefault('res.partner', {})
            demo_data['account.move'] = demo_data.pop('account.move')
            demo_data['res.partner'].setdefault('base.res_partner_2', {})
            demo_data['res.partner']['base.res_partner_2']['l10n_ar_afip_responsibility_type_id'] = 'l10n_ar.res_IVARI'
            demo_data['res.partner'].setdefault('base.res_partner_12', {})
            demo_data['res.partner']['base.res_partner_12']['l10n_ar_afip_responsibility_type_id'] = 'l10n_ar.res_IVARI'
        return demo_data

    @api.model
    def _get_demo_data_move(self, company=False):
        data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == "AR":
            data['demo_invoice_5']['l10n_latam_document_number'] = '1-1'
            data['demo_invoice_equipment_purchase']['l10n_latam_document_number'] = '1-2'
        return data

    def _post_load_demo_data(self, company=False):
        if company not in (
            self.env.ref('l10n_ar.company_mono', raise_if_not_found=False),
            self.env.ref('l10n_ar.company_exento', raise_if_not_found=False),
            self.env.ref('l10n_ar.company_ri', raise_if_not_found=False),
        ):
            # Do not load generic demo data on these companies
            return super()._post_load_demo_data(company)
