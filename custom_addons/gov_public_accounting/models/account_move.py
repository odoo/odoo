from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("date", "journal_id", "state")
    def _check_journal_lock_date(self):
        public_moves = self.filtered(
            lambda move: move.company_id and move.company_id.gov_public_accounting_enabled
        )
        if public_moves:
            super(AccountMove, public_moves)._check_journal_lock_date()
