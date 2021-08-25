# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_account_move(self, balancing_account=False, amount_to_balance=0):
        data = super()._create_account_move(balancing_account, amount_to_balance)
        move = self.move_id
        if move.country_code == "IN":
            company_unit_partner = (
                move.journal_id.l10n_in_gstin_partner_id
                or move.journal_id.company_id.partner_id
            )
            move.write({'l10n_in_gst_treatment': 'consumer', 'l10n_in_state_id': company_unit_partner.state_id})
        return data
