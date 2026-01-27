from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    table_id = fields.Many2one(
        "pos.restaurant.table",
        string="Table",
        help="Restaurant table for this order (self-order).",
    )
    is_self_order = fields.Boolean(
        string="Is Self Order",
        default=False,
        help="Flag to indicate this order was created from self-order site.",
    )
    kitchen_ticket_ids = fields.One2many(
        "restaurant.kitchen_ticket",
        "order_id",
        string="Kitchen Tickets",
    )

    @api.model
    def create_from_self_order(self, values):
        values = dict(values)
        values.setdefault("is_self_order", True)
        order = self.create(values)
        return order
