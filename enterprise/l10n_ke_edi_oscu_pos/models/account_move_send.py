from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_oscu_applicable(self, move):
        return super()._is_oscu_applicable(move) and not move.pos_order_ids
