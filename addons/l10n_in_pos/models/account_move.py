# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('pos_session_ids', 'reversed_pos_order_id')
    def _compute_l10n_in_state_id(self):
        res = super()._compute_l10n_in_state_id()
        to_compute = self.filtered(lambda m: m.country_code == 'IN' and not m.l10n_in_state_id and m.journal_id.type == 'general' and (m.pos_session_ids or m.reversed_pos_order_id))
        for move in to_compute:
            move.l10n_in_state_id = move.company_id.state_id
        return res
