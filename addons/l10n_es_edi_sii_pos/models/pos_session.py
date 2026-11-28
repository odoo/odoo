from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_session_account_move(self, orders):
        move = super()._create_session_account_move(orders)
        if not move or self.company_id._l10n_es_pos_get_fiscal_mode() != 'sii':
            return move

        simplified_orders = orders.filtered('sequence_number').sorted('sequence_number')
        if simplified_orders:
            move.write({
                'l10n_es_invoice_type': 'F4',
                'first_invoice': simplified_orders[0]._l10n_es_pos_get_simplified_invoice_name(),
                'last_invoice': simplified_orders[-1]._l10n_es_pos_get_simplified_invoice_name(),
            })
        return move
