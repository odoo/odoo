from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self.journal_id.debit_sequence:
            where_string += " AND debit_origin_id IS " + ("NOT NULL" if self.debit_origin_id else "NULL")
        return where_string, param

    def _get_starting_sequence(self):
        starting_sequence = super()._get_starting_sequence()
        if (
            self.journal_id.debit_sequence
            and self.debit_origin_id
            and self.move_type in ("in_invoice", "out_invoice")
        ):
            starting_sequence = "D" + starting_sequence
        return starting_sequence
