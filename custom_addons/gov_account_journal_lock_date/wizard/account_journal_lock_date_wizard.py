from odoo import fields, models


class AccountJournalLockDateWizard(models.TransientModel):
    _name = "account.journal.lock.date.wizard"
    _description = "Account Journal Lock Date Wizard"

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        required=True,
        readonly=True,
    )
    journal_lock_date = fields.Date(string="Journal Lock Date")
    lock_date_note = fields.Char(string="Reason")

    def action_apply(self):
        self.ensure_one()
        vals = {
            "journal_lock_date": self.journal_lock_date,
            "lock_date_note": self.lock_date_note,
        }
        self.journal_id.write(vals)
        if hasattr(self.journal_id, "message_post"):
            note = self.lock_date_note or "Journal lock date updated."
            try:
                self.journal_id.message_post(
                    body=(
                        "Journal lock date set to %s. %s"
                        % (self.journal_lock_date or "-", note)
                    )
                )
            except Exception:
                pass
        return {"type": "ir.actions.act_window_close"}

