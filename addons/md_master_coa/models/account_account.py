from odoo import fields, models


class AccountAccount(models.Model):
    """Extend account.account to hold a reference back to the master COA."""
    _inherit = 'account.account'

    master_account_id = fields.Many2one(
        'md.master.account',
        string='Master COA Account',
        index=True,
        ondelete='set null',
        help='Link to the MD Portfolio Master Chart of Accounts entry. '
             'Used for cross-company reporting and QBO synchronisation.')
    master_sync_state = fields.Selection(
        related='master_account_id.qbo_sync_state',
        string='QBO Sync State',
        readonly=True, store=False)
