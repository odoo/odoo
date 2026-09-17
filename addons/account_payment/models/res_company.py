from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Intercompany clearing
    account_interco_clearing_journal_id = fields.Many2one(
        comodel_name='account.journal',
        check_company=True,
        string='Intercompany Clearing Journal',
        domain=[('type', '=', 'general')],
        help='The accounting journal where Intercompany payments will be cleared',
    )
    account_interco_payable_id = fields.Many2one(
        comodel_name='account.account',
        string="Intercompany Clearing Payable Account",
        domain=[('account_type', '=', 'liability_payable'), ('reconcile', '=', True)],
        help='The account where Intercompany invoice payments will be cleared',
    )
    account_interco_receivable_id = fields.Many2one(
        comodel_name='account.account',
        string="Intercompany Clearing Receivable Account",
        domain=[('account_type', '=', 'asset_receivable'), ('reconcile', '=', True)],
        help='The account where Intercompany credit note payments will be cleared',
    )
