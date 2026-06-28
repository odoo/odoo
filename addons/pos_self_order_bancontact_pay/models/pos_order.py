from odoo import Command, api, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _check_pos_order_payments(self, pos_config, order, payment):
        result = super()._check_pos_order_payments(pos_config, order, payment)
        if payment[0] in [Command.CREATE, Command.UPDATE]:
            result[2]["bancontact_id"] = payment[2].get("bancontact_id")
        return result
