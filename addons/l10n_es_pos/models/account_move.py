# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import point_of_sale, l10n_es


class AccountMove(point_of_sale.AccountMove, l10n_es.AccountMove):

    def _compute_l10n_es_is_simplified(self):
        super()._compute_l10n_es_is_simplified()
        for move in self:
            if move.pos_order_ids:
                move.l10n_es_is_simplified = move.pos_order_ids[0].is_l10n_es_simplified_invoice
