from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("date", "journal_id", "state")
    def _check_journal_lock_date(self):
        if self.env.user.has_group(
            "gov_account_journal_lock_date.group_account_journal_lock_manager"
        ):
            return
        posted_moves = self.filtered(
            lambda move: move.state == "posted" and move.date and move.journal_id
        )
        for move in posted_moves:
            lock_date = move.journal_id._get_journal_lock_date()
            if lock_date and move.date <= lock_date:
                lock_date_display = format_date(self.env, lock_date)
                raise UserError(
                    "Journal %s is locked until %s. "
                    "Contact your accountant to unlock it."
                    % (move.journal_id.display_name, lock_date_display)
                )


