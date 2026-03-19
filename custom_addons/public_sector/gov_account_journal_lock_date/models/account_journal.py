from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    journal_lock_date = fields.Date(
        string="Journal Lock Date",
        help=(
            "Journal entries on or before this date cannot be posted "
            "unless the user has journal lock manager privileges."
        ),
    )
    lock_date_note = fields.Char(string="Lock Date Note")

    def _get_journal_lock_date(self):
        self.ensure_one()
        lock_dates = [d for d in [self.journal_lock_date, self.company_id.fiscalyear_lock_date] if d]
        if not lock_dates:
            return False
        return max(lock_dates)

    def action_open_lock_date_wizard(self):
        self.ensure_one()
        action = self.env.ref(
            "gov_account_journal_lock_date.account_journal_lock_date_wizard_action",
            raise_if_not_found=False,
        )
        if not action:
            return False
        action_values = action.read()[0]
        action_values["context"] = {
            "default_journal_id": self.id,
            "default_journal_lock_date": self.journal_lock_date,
            "default_lock_date_note": self.lock_date_note,
        }
        return action_values


