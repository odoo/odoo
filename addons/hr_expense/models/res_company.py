# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    employee_paid_expense_journal_id = fields.Many2one(
        "account.journal",
        string="Employee Expense Journal",
        check_company=True,
        domain="[('type', '=', 'purchase')]",
        help="The company's default journal used when an employee expense paid by the employee is created.",
    )
    company_paid_expense_journal_id = fields.Many2one(
        "account.journal",
        string="Company Expense Journal",
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        help="The company's default journal used when an employee expense paid by the company is created.",
    )
    company_expense_allowed_payment_method_ids = fields.Many2many(
        "account.payment.method",
        string="Payment methods available for expenses paid by company",
        domain="[('payment_type', '=', 'outbound')]",
    )
