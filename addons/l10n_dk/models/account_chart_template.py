# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        res = super(AccountChartTemplate, self)._prepare_transfer_account_for_direct_creation(name, company)
        # if company.country_id.code == 'DK':
        account_group_liquidity = self.env.ref('l10n_dk.account_group_liquidity', raise_if_not_found=False)
        current_assets_type = self.env.ref('account.data_account_type_liquidity', raise_if_not_found=False)
           
        res['group_id'] = account_group_liquidity.id
        res['name'] = 'Bank i transfer'
        res['user_type_id'] = current_assets_type.id

        return res
