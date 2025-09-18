from odoo import api, fields, models


class PurchaseMassCancelOrders(models.TransientModel):
    _name = "purchase.mass.cancel.orders"
    _description = "Cancel multiple RFQs/purchase orders"

    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        relation="purchase_order_mass_cancel_wizard_rel",
        string="Purchase orders to cancel",
        default=lambda self: self.env.context.get("active_ids"),
    )
    purchase_orders_count = fields.Integer(compute="_compute_purchase_orders_count")
    has_confirmed_order = fields.Boolean(compute="_compute_has_confirmed_order")

    @api.depends("purchase_order_ids")
    def _compute_purchase_orders_count(self):
        for wizard in self:
            wizard.purchase_orders_count = len(wizard.purchase_order_ids)

    @api.depends("purchase_order_ids")
    def _compute_has_confirmed_order(self):
        for wizard in self:
            wizard.has_confirmed_order = bool(
                wizard.purchase_order_ids.filtered(lambda po: po.state == "done"),
            )

    def action_mass_cancel(self):
        self.purchase_order_ids._action_cancel()
