# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_payment_acquirer_account(self):
        # OVERRIDE
        vals = super()._prepare_payment_acquirer_account()
        if self.env.company.account_fiscal_country_id.code == 'DE':
            vals.setdefault('tag_ids', [])
            vals['tag_ids'].append((4, self.env.ref('l10n_de.tag_de_asset_bs_B_III_2').id))
        return vals

    def _update_company_before_loading(self):
        # OVERRIDE
        # Write paperformat and report template used on company
        company = self.env.company
        res = super()._update_company_before_loading()
        if company.account_fiscal_country_id.code == 'DE':
            company.write({
                'external_report_layout_id': self.env.ref('l10n_de.external_layout_din5008').id,
                'paperformat_id': self.env.ref('l10n_de.paperformat_euro_din').id,
            })
        return res
