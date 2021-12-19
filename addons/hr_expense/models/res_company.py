# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    expense_journal_id = fields.Many2one('account.journal', string='Default Expense Journal', check_company=True, domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="The Default journal for the company used when the expense is done.")
