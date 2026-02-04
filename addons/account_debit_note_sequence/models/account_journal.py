from odoo.tools.sql import column_exists, create_column
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

    def _auto_init(self):
        """
        Create column for `debit_sequence` to avoid having it
        computed by the ORM on installation. Since `debit_sequence` is
        introduced in this module, there is no need for UPDATE
        and we don't want to change the sequence of existing journals
        in stable.
        """
        if not column_exists(self.env.cr, "account_journal", "debit_sequence"):
            create_column(self.env.cr, "account_journal", "debit_sequence", "boolean")
        return super()._auto_init()

    @api.depends("type")
    def _compute_debit_sequence(self):
        for journal in self:
            journal.debit_sequence = journal.type in ("sale", "purchase")
