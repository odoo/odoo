#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account', company_dependent=True)
    account_debit = fields.Many2one(
        'account.account', 'Debit Account', company_dependent=True, domain=[('deprecated', '=', False)], ondelete='restrict')
    account_credit = fields.Many2one(
        'account.account', 'Credit Account', company_dependent=True, domain=[('deprecated', '=', False)], ondelete='restrict')
    not_computed_in_net = fields.Boolean(
        string="Not computed in net accountably", default=False,
        help='This field allows you to delete the value of this rule in the "Net Salary" rule at the accounting level to explicitly display the value of this rule in the accounting. For example, if you want to display the value of your representation fees, you can check this field.')
    debit_tag_ids = fields.Many2many(
        string="Debit Tax Grids",
        comodel_name='account.account.tag',
        relation='hr_salary_rule_debit_tag_rel',
        help="Tags assigned to this line will impact financial reports when translated into an accounting journal entry."
            "They will be applied on the debit account line in the journal entry.",
    )
    credit_tag_ids = fields.Many2many(
        string="Credit Tax Grids",
        comodel_name='account.account.tag',
        relation='hr_salary_rule_credit_tag_rel',
        help="Tags assigned to this line will impact financial reports when translated into an accounting journal entry."
            "They will be applied on the credit account line in the journal entry.",
    )
    split_move_lines = fields.Boolean(
        string="Split account line based on name",
        help="Enable this option to split the accountig entries for this rule according to the payslip line name. It could be useful for deduction/reimbursement or salary attachments for instance.")
