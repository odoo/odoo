# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'analytic_account_id', 'Budget Lines')
