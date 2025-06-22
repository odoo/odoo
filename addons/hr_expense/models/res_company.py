# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_product_id = fields.Many2one(
        "product.product",
        string="Default Expense Category",
        check_company=True,
        domain="[('can_be_expensed', '=', True)]",
    )
    expense_journal_id = fields.Many2one(
        "account.journal",
        string="Default Expense Journal",
        check_company=True,
        domain="[('type', '=', 'purchase')]",
        help="The company's default journal used when an employee expense is created.",
    )
    company_expense_allowed_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line",
        string="Payment methods available for expenses paid by company",
        check_company=True,
        domain="[('payment_type', '=', 'outbound'), ('journal_id', '!=', False), ('journal_id.active', '=', True)]",
    )
