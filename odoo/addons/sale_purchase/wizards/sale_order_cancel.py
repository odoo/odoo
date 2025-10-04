from odoo import api, fields, models


class SaleOrderCancel(models.TransientModel):
    _inherit = "sale.order.cancel"

    display_purchase_orders_alert = fields.Boolean(
        string="Purchase Order Alert",
        compute='_compute_display_purchase_orders_alert',
        groups='purchase.group_purchase_user'
    )

    @api.depends('order_id')
    def _compute_display_purchase_orders_alert(self):
        for wizard in self:
            wizard.display_purchase_orders_alert = bool(
                wizard.order_id.purchase_order_count
            )
