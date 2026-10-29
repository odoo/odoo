from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_journal_id = fields.Many2one('account.journal', related='company_id.expense_journal_id', readonly=False, check_company=True, domain="[('type', '=', 'purchase')]")
    company_expense_allowed_payment_method_line_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        check_company=True,
        related='company_id.company_expense_allowed_payment_method_line_ids',
        readonly=False,
        domain="[('payment_type', '=', 'outbound'), ('journal_id.active', '=', True)]",
    )
