# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_journal_id = fields.Many2one(
        "account.journal",
        string="Default Expense Journal",
        check_company=True,
        domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="The company's default journal used when an employee expense is created.",
    )
    company_expense_allowed_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line",
        string="Payment methods available for expenses paid by company",
        check_company=True,
        domain="[('payment_type', '=', 'outbound'), ('company_id', '=', company_id),('journal_id', '!=', False)]",
    )
