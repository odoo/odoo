# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_for_direct_creation(name, company)
        if company.account_fiscal_country_id.code == 'DK':
            account_tag_liquidity = self.env.ref('l10n_dk.account_tag_liquidity')
            res['tag_ids'] = [(6, 0, account_tag_liquidity.ids)]
            res['name'] = 'Bank i transfer'
        return res
