# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        if self.user_has_groups('account.group_account_readonly'):
            result['search_params']['fields'].extend(['credit_limit', 'total_due', 'use_partner_credit_limit'])
        return result

    def _loader_params_res_company(self):
        result = super()._loader_params_res_company()
        if self.user_has_groups('account.group_account_readonly'):
            result['search_params']['fields'].extend(['account_use_credit_limit'])
        return result

    def _get_pos_ui_res_partner(self, params):
        partners_list = super()._get_pos_ui_res_partner(params)
        if self.config_id.currency_id != self.env.company.currency_id and self.user_has_groups('account.group_account_readonly'):
            for partner in partners_list:
                partner['total_due'] = self.env.company.currency_id._convert(partner['total_due'], self.config_id.currency_id, self.env.company, fields.Date.today())
        return partners_list
