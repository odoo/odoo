from odoo import api, fields, models


class MixinOrderMassCancel(models.AbstractModel):
    _name = "mixin.order.mass.cancel"
    _description = "Cancel Multiple Orders"

    orders_count = fields.Count(count_of="order_ids")
    has_confirmed_order = fields.Boolean(compute="_compute_has_confirmed_order")

    @api.depends("order_ids")
    def _compute_has_confirmed_order(self):
        for wizard in self:
            wizard.has_confirmed_order = bool(
                wizard.order_ids.filtered(lambda order: order.state == "done"),
            )

    def action_mass_cancel(self):
        self.order_ids.filtered(lambda order: order.state != "cancel").action_cancel()
        return {"type": "ir.actions.act_window_close"}
