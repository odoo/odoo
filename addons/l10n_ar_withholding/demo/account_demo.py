# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, template_code):
        super()._post_load_demo_data(template_code)
        if template_code == 'ar_ri':
            # Because in demo we want to skip the config, while in data we want to require them to configure
            self._ar_withholding_copy_tax_demo()

    def _ar_withholding_copy_tax_demo(self):
        self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(self.env.company),
            ('l10n_ar_withholding_payment_type', '!=', False),
            ('l10n_ar_tax_type', 'in', ('iibb_untaxed', 'iibb_total')),
        ]).copy(default={'amount_type': 'percent', 'amount': 1})

    @template(template='ar_ri', model='ir.sequence', demo=True)
    def _get_ar_withholding_ir_sequence_demo(self):
        return {
            'earning_wth_sequence': {
                'name': 'Earnings wth sequence',
                'padding': 1,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': self.env.company.id,
            },
        }

    @template(template='ar_ri', model='account.tax', demo=True)
    def _get_ar_witholding_account_tax_demo(self):
        return {
            'ex_tax_withholding_profits_regimen_119_insc': {'l10n_ar_withholding_sequence_id': 'earning_wth_sequence'},
            'ex_tax_withholding_profits_regimen_78_insc': {'l10n_ar_withholding_sequence_id': 'earning_wth_sequence'},
        }

    @template(template='ar_ri', model='l10n_ar.partner.tax', demo=True)
    def _get_ar_withholding_partner_tax_demo(self):
        return {
            'partner_tax_adhoc_119': {
                'tax_id': 'ex_tax_withholding_profits_regimen_119_insc',
                'partner_id': 'l10n_ar.res_partner_adhoc',
            },
            'partner_tax_adhoc_iibb': {
                'tax_id': 'ex_tax_withholding_iibb_ba_applied',
                'partner_id': 'l10n_ar.res_partner_adhoc',
            },
            'partner_tax_mipyme_78': {
                'tax_id': 'ex_tax_withholding_profits_regimen_78_insc',
                'partner_id': 'l10n_ar.res_partner_mipyme',
            },
            'partner_tax_mipyme_iibb': {
                'tax_id': 'ex_tax_withholding_iibb_ba_applied',
                'partner_id': 'l10n_ar.res_partner_mipyme',
            },
        }
