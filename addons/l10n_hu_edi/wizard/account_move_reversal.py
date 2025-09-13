from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if move.company_id.account_fiscal_country_id.code == "HU":
            res.update({
                'delivery_date': move.delivery_date
            })
        return res

    def reverse_moves(self, is_modify=False):
        action = super().reverse_moves(is_modify=is_modify)
        if is_modify:
            # In Hungary, if we do `Reverse and Create Invoice`, the new invoice should have a debit_origin_id pointing to the old invoice.
            # Match new invoices to old invoices based on (move_type, journal_id, partner_id, amount_total_in_currency_signed).
            for origin in self.move_ids.filtered(lambda m: m.l10n_hu_edi_state):
                matched_new_move = self.new_move_ids.filtered(
                    lambda m: (
                        (m.move_type, m.journal_id, m.partner_id, m.amount_total_in_currency_signed)
                        == (origin.move_type, origin.journal_id, origin.partner_id, origin.amount_total_in_currency_signed)
                    )
                )
                matched_new_move.write({'debit_origin_id': origin.id})
        return action
