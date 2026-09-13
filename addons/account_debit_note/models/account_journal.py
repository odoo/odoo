from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    debit_sequence = fields.Boolean(
        string="Dedicated Debit Note Sequence",
        help="Check this box if you don't want to share the same sequence for invoices "
        "and debit notes made from this journal",
        compute="_compute_debit_sequence",
        store=True,
        readonly=False,
    )

    @api.depends("type")
    def _compute_debit_sequence(self):
        for journal in self:
            journal.debit_sequence = journal.type in ("sale", "purchase")
