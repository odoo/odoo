# -*- coding: utf-8 -*-
from odoo import models
import re


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        result = super()._post_load_demo_data(company)
        if company == self.env.ref('base.company_ri', raise_if_not_found=False):
            profits_wth_tax_119 = self.with_company(company).ref('ex_tax_withholding_profits_regimen_119_insc')

            # Add to partner Adhoc: 1) wth tax 119 and it`s sequence, 2) arba wth
            self.env['l10n_ar.partner.tax'].create({'tax_id': profits_wth_tax_119.id, 'partner_id': self.env.ref('l10n_ar.res_partner_adhoc').id, 'company_id': company.id})

            # Add to partner Belgrano: 1) wth tax 78 and it`s sequence, 2) arba wth
            profits_wth_tax_78 = self.with_company(company).ref('ex_tax_withholding_profits_regimen_78_insc')
            self.env['l10n_ar.partner.tax'].create({'tax_id': profits_wth_tax_78.id, 'partner_id': self.env.ref('l10n_ar.res_partner_mipyme').id, 'company_id': company.id})

            # Because in demo we want to skip the config, while in data we want to require them to configure
            for tax in self.env['account.tax'].search([('l10n_ar_withholding_payment_type', '!=', False), ('l10n_ar_tax_type', 'in', ('iibb_untaxed', 'iibb_total'))]):
                name = re.sub(r'\b\d+(\.\d+)?\s*%', '1%', tax.name)
                tax.copy(default={'amount_type': 'percent', 'amount': 1, 'name': name})
        return result
