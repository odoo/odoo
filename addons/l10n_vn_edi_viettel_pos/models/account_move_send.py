# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_vn_edi_applicable(self, move):
        res = super()._is_vn_edi_applicable(move)

        if not move.sudo().pos_order_ids:
            return res

        pos_ok = all(
            config.l10n_vn_auto_send_to_sinvoice and (config.l10n_vn_pos_symbol or config.company_id.l10n_vn_pos_default_symbol)
            for config in move.sudo().pos_order_ids.mapped('config_id')
        )

        return res and pos_ok
