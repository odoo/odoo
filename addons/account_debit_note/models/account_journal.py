from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    debit_sequence = fields.Boolean(
        string="Dedicated Debit Note Sequence",
        help="Check this box if you don't want to share the same sequence for invoices "
        "and debit notes made from this journal",
        default=False,
    )

    @api.onchange("type")
    def _onchange_type(self):
        super()._onchange_type()
        self.debit_sequence = self.type in ("sale", "purchase")

    @api.model
    def _fill_missing_values(self, vals, protected_codes=False):
        super()._fill_missing_values(vals, protected_codes)
        # === Fill missing debit_sequence (similar to refund_sequence) ===
        if "debit_sequence" not in vals:
            vals["debit_sequence"] = vals["type"] in ("sale", "purchase")
