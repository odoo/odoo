# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('pos_session_ids')
    def _compute_kode_transaksi(self):
        """ Set PoS transaction code to False, since it will be reported in bulk. """
        pos_moves = self.filtered('pos_session_ids')
        pos_moves.l10n_id_kode_transaksi = False
        super(AccountMove, self - pos_moves)._compute_kode_transaksi()
