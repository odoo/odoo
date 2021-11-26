# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.http import request

class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def try_loading(self, company=False, install_demo=True):

        if not self == self.env.ref('l10n_uk.l10n_uk'):
            return super().try_loading(company, install_demo)
        else:
            # Determine whether the country of the company is Northern Ireland
            if not company:
                if request and hasattr(request, 'allowed_company_ids'):
                    company = self.env['res.company'].browse(request.allowed_company_ids[0])
                else:
                    company = self.env.company

        try:
            # If base has updated, then Northern Ireland will exist as a country code
            # otherwise .ref('base.xi') will cause an exception
            uk_fiscal_country = (company.account_fiscal_country_id == self.env.ref('base.uk') or
                                 company.account_fiscal_country_id == self.env.ref('base.xi'))
            use_northern_ireland_coa = uk_fiscal_country and company.country_id == self.env.ref('base.xi')
        except:
            use_northern_ireland_coa = False

        # If we don't have any chart of account on this company, install this chart of account
        if not company.chart_template_id and not self.existing_accounting(company):
            for template in self:
                # The NI CoA is in l10n_uk, we want to load it if the country is Northern Ireland
                if use_northern_ireland_coa:
                    template = self.env.ref('l10n_uk.l10n_uk_ni')
                template.with_context(default_company_id=company.id)._load(15.0, 15.0, company)

            # Install the demo data when the first localization is instanciated on the company
            if install_demo and self.env.ref('base.module_account').demo:
                self.with_context(
                    default_company_id=company.id,
                    allowed_company_ids=[company.id],
                )._create_demo_data()

            else:
                return super().try_loading(company, install_demo)
