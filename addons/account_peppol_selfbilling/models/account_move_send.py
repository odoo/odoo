from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_move_constraints(self, move):
        constraints = super()._get_move_constraints(move)
        if move._is_exportable_as_self_invoice():
            constraints.pop('not_sale_document', None)
        return constraints
