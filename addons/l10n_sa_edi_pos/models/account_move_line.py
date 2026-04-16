from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_sa_is_gift_card_or_ewallet_line(self):
        # EXTENDS l10n_sa_edi
        if super()._l10n_sa_is_gift_card_or_ewallet_line():
            return True
        pos_lines = self.move_id.sudo().pos_order_ids.lines
        if 'reward_id' not in pos_lines._fields:
            return False
        # An invoice line has no link to its POS order line: match the reward product, as pos_loyalty does.
        payment_lines = pos_lines.filtered(lambda line: line.reward_id.program_type in {'gift_card', 'ewallet'})
        return self.product_id in payment_lines.product_id
