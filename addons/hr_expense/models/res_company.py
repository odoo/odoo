# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_journal_id = fields.Many2one(
        "account.journal",
        string="Default Expense Journal",
        check_company=True,
        domain="[('type', '=', 'purchase')]",
        help="The company's default journal used when an employee expense is created.",
    )
    expense_outstanding_account_id = fields.Many2one(
        "account.account",
        string="Outstanding Account",
        check_company=True,
        domain="[('account_type', '=', 'asset_current'), ('reconcile', '=', True)]",
        help="The account used to record the outstanding amount of the employee expenses.",
    )
    company_expense_allowed_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line",
        string="Payment methods available for expenses paid by company",
        check_company=True,
        domain="[('payment_type', '=', 'outbound'), ('journal_id', '!=', False)]",
    )
