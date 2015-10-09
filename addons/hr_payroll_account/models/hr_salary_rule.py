# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryRule(models.Model):

    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    account_tax_id = fields.Many2one('account.tax', string='Tax')
    account_debit = fields.Many2one('account.account', string='Debit Account', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', string='Credit Account', domain=[('deprecated', '=', False)])
