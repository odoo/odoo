from odoo import api, models


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)

        default_group_id = self.default_get(['group_id']).get('group_id')
        if default_group_id:
            for move in pickings.move_ids:
                move.group_id = default_group_id

        return pickings
