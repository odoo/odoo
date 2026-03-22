from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # ref: public_sector/gov_account_journal_lock_date/models/account_journal.py
    lock_date_br = fields.Date(
        string="Data de Bloqueio BR",
        help="Bloqueia contabilizacoes nesta data ou anteriores para este diario.",
    )

