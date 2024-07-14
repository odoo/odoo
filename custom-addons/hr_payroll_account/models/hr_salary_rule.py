#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account', company_dependent=True)
    account_debit = fields.Many2one(
        'account.account', 'Debit Account', company_dependent=True, domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one(
        'account.account', 'Credit Account', company_dependent=True, domain=[('deprecated', '=', False)])
    not_computed_in_net = fields.Boolean(
        string="Not computed in net accountably", default=False,
        help='This field allows you to delete the value of this rule in the "Net Salary" rule at the accounting level to explicitly display the value of this rule in the accounting. For example, if you want to display the value of your representation fees, you can check this field.')
