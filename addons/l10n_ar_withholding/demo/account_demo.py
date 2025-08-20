# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        result = super()._post_load_demo_data(company)
        if company == self.env.ref('base.company_ri', raise_if_not_found=False):
            profits_wth_tax_119 = self.with_company(company).ref('ex_tax_withholding_profits_regimen_119_insc')
            pba_wth_applied = self.with_company(company).ref('ex_tax_withholding_iibb_ba_applied')
            # Create demo sequence for earnings wth
            seq_profits_wth = self.env['ir.sequence'].create({
                'name': 'Earnings wth sequence',
                'padding': 1,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': self.env.ref('base.company_ri').id
            })
            wth_sequence_id = seq_profits_wth.id

            # Add to partner Adhoc: 1) wth tax 119 and it`s sequence, 2) pba wth
            self.env['l10n_ar.partner.tax'].create({'tax_id': profits_wth_tax_119.id, 'partner_id': self.env.ref('l10n_ar.res_partner_adhoc').id, 'company_id': company.id})
            profits_wth_tax_119.l10n_ar_withholding_sequence_id = wth_sequence_id
            self.env['l10n_ar.partner.tax'].create({'tax_id': pba_wth_applied.id, 'partner_id': self.env.ref('l10n_ar.res_partner_adhoc').id, 'company_id': company.id})

            # Add to partner Belgrano: 1) wth tax 78 and it`s sequence, 2) pba wth
            earnings_wth_tax_78 = self.with_company(company).ref('ex_tax_withholding_profits_regimen_78_insc')
            self.env['l10n_ar.partner.tax'].create({'tax_id': earnings_wth_tax_78.id, 'partner_id': self.env.ref('l10n_ar.res_partner_mipyme').id, 'company_id': company.id})
            earnings_wth_tax_78.l10n_ar_withholding_sequence_id = wth_sequence_id
            self.env['l10n_ar.partner.tax'].create({'tax_id': pba_wth_applied.id, 'partner_id': self.env.ref('l10n_ar.res_partner_mipyme').id, 'company_id': company.id})

        return result
