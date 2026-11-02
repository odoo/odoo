# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

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

    @api.constrains('expense_journal_id')
    def _check_expense_journal_id_type(self):
        for company in self:
            if company.expense_journal_id and company.expense_journal_id.type != 'purchase':
                raise ValidationError(
                    self.env._("The employee expense journal must be a purchase journal.")
                )
