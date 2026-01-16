from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _move_has_pos_settlement(self, move):
        return bool(move.pos_order_ids.lines.settled_order_id)

    @api.model
    def _is_sa_edi_applicable(self, move):
        res = super()._is_sa_edi_applicable(move)
        if not self.env['pos.order.line']._fields.get('settled_order_id'):
            return res

        # Currently we are blocking settle due and new purchase on the same order from the UI
        return bool(move.pos_order_ids.lines.settled_order_id) and res
