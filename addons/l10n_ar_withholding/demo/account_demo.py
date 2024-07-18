# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        result = super()._post_load_demo_data(company)
        if company == self.env.ref('base.company_ri', raise_if_not_found=False):
            earnings_withholding_tax_119 = self.env.ref(f'account.{company.id}_ri_tax_withholding_earnings_incurred_group_119_insc')
            arba_withholding_applied = self.env.ref(f'account.{company.id}_ri_tax_withholding_iibb_ba_applied')
            # Create demo sequence for earnings withholding
            seq_earnings_withholding = self.env['ir.sequence'].create({
                'name': 'Earnings withholding sequence',
                'padding': 1,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': self.env.ref('base.company_ri').id
            })
            withholding_sequence_id = seq_earnings_withholding.id

            # Add to partner Adhoc: 1) withholding tax 119 and it`s sequence, 2) arba withholding
            self.env['l10n_ar.partner.tax'].create({'tax_id': earnings_withholding_tax_119.id, 'partner_id': self.env.ref('l10n_ar.res_partner_adhoc').id, 'company_id': company.id})
            earnings_withholding_tax_119.l10n_ar_withholding_sequence_id = withholding_sequence_id
            self.env['l10n_ar.partner.tax'].create({'tax_id': arba_withholding_applied.id, 'partner_id': self.env.ref('l10n_ar.res_partner_adhoc').id, 'company_id': company.id})

            # Add to partner Belgrano: 1) withholding tax 78 and it`s sequence, 2) arba withholding
            earnings_withholding_tax_78 = self.env.ref(f'account.{company.id}_ri_tax_withholding_earnings_incurred_group_78_insc')
            self.env['l10n_ar.partner.tax'].create({'tax_id': earnings_withholding_tax_78.id, 'partner_id': self.env.ref('l10n_ar.res_partner_mipyme').id, 'company_id': company.id})
            earnings_withholding_tax_78.l10n_ar_withholding_sequence_id = withholding_sequence_id
            self.env['l10n_ar.partner.tax'].create({'tax_id': arba_withholding_applied.id, 'partner_id': self.env.ref('l10n_ar.res_partner_mipyme').id, 'company_id': company.id})

            # Because in demo we want to skip the config, while in data we want to require them to configure
            self.env['account.tax'].search([('l10n_ar_withholding_payment_type', '!=', False), ('l10n_ar_tax_type', 'in', ('iibb_withholding_untaxed', 'iibb_withholding_total'))]).write({'amount_type': 'percent', 'amount' : 1})
        return result
