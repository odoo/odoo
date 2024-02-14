# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class Account(models.Model):
    _inherit = 'account.account'


    @api.depends('account_type')
    def _compute_include_initial_balance(self):
        super()._compute_include_initial_balance()
        for account in self.filtered(lambda x: x.company_id.country_code == 'CL'):
            account.include_initial_balance &= account.account_type != 'equity_unaffected'
