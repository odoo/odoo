from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Default Expense Journal",
        domain="[('type', '=', 'purchase')]",
        check_company=True,
        help="The company's default journal used when an employee expense is created.",
    )
    company_expense_allowed_payment_channel_ids = fields.Many2many(
        comodel_name="account.payment.channel",
        string="Payment methods available for expenses paid by company",
        domain="[('payment_type', '=', 'outbound'), ('journal_id', '!=', False), ('journal_id.active', '=', True)]",
        check_company=True,
    )
