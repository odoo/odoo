# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_l10n_es_invoice_type(self):
        # EXTENDS 'l10n_es'
        super()._compute_l10n_es_invoice_type()
        for move in self:
            if move.pos_order_ids:
                is_simplified = move.pos_order_ids[0].is_l10n_es_simplified_invoice
                if move.move_type in ('out_invoice', 'in_invoice'):
                    move.l10n_es_invoice_type = 'F2' if is_simplified else 'F1'
                elif move.move_type in ('out_refund', 'in_refund'):
                    move.l10n_es_invoice_type = 'R5' if is_simplified else 'R4'
