# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _prepare_session_move_vals(self, orders):
        # EXTENDS point_of_sale
        # Link the receipt of the sales to the session as soon as it's created rather than once it's
        # paid, so that its bank payments know the receipt they pay, see pos.payment.method.
        move_vals = super()._prepare_session_move_vals(orders)
        if move_vals['move_type'] == 'out_invoice' and self.company_id.country_code == 'PH':
            move_vals['pos_session_sales_id'] = self.id
        return move_vals

    def _create_session_account_move(self, orders):
        # EXTENDS point_of_sale
        # Let the bank payments of the orders withhold on the receipt, see pos.payment.method.
        session = self.with_context(l10n_ph_pos_closing_session_id=self.id)
        return super(PosSession, session)._create_session_account_move(orders.with_context(l10n_ph_pos_closing_session_id=self.id))
