from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    debit_sequence = fields.Boolean(
        string="Dedicated Debit Note Sequence",
        compute="_compute_debit_sequence",
        readonly=False, store=True,
        help="Check this box if you don't want to share the same sequence for invoices "
        "and debit notes made from this journal",
    )

    @api.depends("type")
    def _compute_debit_sequence(self):
        for journal in self:
            journal.debit_sequence = journal.type in ("sale", "purchase")
