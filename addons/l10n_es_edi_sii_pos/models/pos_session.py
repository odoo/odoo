from odoo import models


class PosSessio(models.Model):
    _inherit = 'pos.session'

    def _create_session_account_move(self, orders):
        move = super()._create_session_account_move(orders)
        if move and orders:
            sorted_orders = orders.sorted('sequence_number')
            move.write({
                'l10n_es_invoice_type': 'F4',
                'first_invoice': sorted_orders[0].pos_reference,
                'last_invoice': sorted_orders[-1].pos_reference,
            })
        return move
