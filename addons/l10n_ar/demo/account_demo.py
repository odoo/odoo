# -*- coding: utf-8 -*-
import logging

from odoo import api, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _l10n_ar_has_static_demo(self):
        # Do not load generic demo data on these companies
        return self.env.company in (
            self.env.ref('base.company_mono', raise_if_not_found=False),
            self.env.ref('base.company_exento', raise_if_not_found=False),
            self.env.ref('base.company_ri', raise_if_not_found=False),
        )

    @template(model='account.move', demo=True)
    def _get_demo_data_move(self, template_code):
        if self._l10n_ar_has_static_demo():
            return {}
        data = super()._get_demo_data_move(template_code)
        if template_code.startswith('ar'):
            data['demo_invoice_8']['l10n_latam_document_number'] = '1-1'
            data['demo_invoice_equipment_purchase']['l10n_latam_document_number'] = '1-2'
            data['demo_move_auto_reconcile_3']['l10n_latam_document_number'] = '1-3'
            data['demo_move_auto_reconcile_4']['l10n_latam_document_number'] = '1-4'
        return data

    @template(model='account.bank.statement', demo=True)
    def _get_demo_data_statement(self, template_code):
        return {} if self._l10n_ar_has_static_demo() else super()._get_demo_data_statement(template_code)

    @template(model='account.bank.statement.line', demo=True)
    def _get_demo_data_transactions(self, template_code):
        return {} if self._l10n_ar_has_static_demo() else super()._get_demo_data_transactions(template_code)

    @template(model='ir.attachment', demo=True)
    def _get_demo_data_attachment(self, template_code):
        return {} if self._l10n_ar_has_static_demo() else super()._get_demo_data_attachment(template_code)

    @template(model='mail.message', demo=True)
    def _get_demo_data_mail_message(self, template_code):
        return {} if self._l10n_ar_has_static_demo() else super()._get_demo_data_mail_message(template_code)

    @template(model='mail.activity', demo=True)
    def _get_demo_data_mail_activity(self, template_code):
        return {} if self._l10n_ar_has_static_demo() else super()._get_demo_data_mail_activity(template_code)

    @template(template='ar_base', model='res.partner', demo=True)
    def _get_ar_demo_partner(self, company=False):
        return {
            'base.res_partner_2': {'l10n_ar_afip_responsibility_type_id': 'l10n_ar.res_IVARI'},
            'base.res_partner_3': {'l10n_ar_afip_responsibility_type_id': 'l10n_ar.res_IVARI'},
            'base.res_partner_4': {'l10n_ar_afip_responsibility_type_id': 'l10n_ar.res_IVARI'},
            'base.res_partner_5': {'l10n_ar_afip_responsibility_type_id': 'l10n_ar.res_IVARI'},
            'base.res_partner_6': {'l10n_ar_afip_responsibility_type_id': 'l10n_ar.res_IVARI'},
            'base.res_partner_12': {'l10n_ar_afip_responsibility_type_id': 'l10n_ar.res_IVARI'},
        }

    def _post_load_demo_data(self, template_code):
        if self._l10n_ar_has_static_demo():
            return None
        return super()._post_load_demo_data(template_code)
