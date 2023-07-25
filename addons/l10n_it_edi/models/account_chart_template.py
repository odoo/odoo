# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def try_loading(self, company=False, install_demo=True):
        """
            Override normal default taxes, which are the ones with lowest sequence.
        """
        if not company:
            if request and hasattr(request, 'allowed_company_ids'):
                company = self.env['res.company'].browse(request.allowed_company_ids[0])
            else:
                company = self.env.company
        self_company = self.with_company(company)

        install_demo_and_base_demo = install_demo and self.env.ref('base.module_account').demo
        if install_demo_and_base_demo and not company.chart_template_id and not self_company.existing_accounting(company):
            fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
            edi_identification = fattura_pa._get_proxy_identification(company)
            self_company.env['account_edi_proxy_client.user']._register_proxy_user(company, fattura_pa, edi_identification)

        super().try_loading(company, install_demo)

        if company.chart_template_id == self.env.ref('l10n_it.l10n_it_chart_template_generic', raise_if_not_found=False):
            company.account_sale_tax_id = self.env.ref(f'l10n_it.{company.id}_22v')
            company.account_purchase_tax_id = self.env.ref(f'l10n_it.{company.id}_22am')

            if install_demo_and_base_demo:
                pa_partner = self_company.env.ref('l10n_it_edi.demo_l10n_it_edi_partner_pa')
                pa_partner.property_account_position_id = self.env.ref(f'l10n_it.{company.id}_split_payment_fiscal_position')
