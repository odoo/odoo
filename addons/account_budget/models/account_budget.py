# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _description = "Budgetary Position"
    _order = "name"
    name = fields.Char(required=True)
    account_ids = fields.Many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', string='Accounts', domain=[('deprecated', '=', False)])
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'general_budget_id', string='Budget Lines')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
