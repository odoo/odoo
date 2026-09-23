from odoo import fields, models
from odoo.tools import SQL


class SaleDeliveryLineMatch(models.Model):
    _name = "sale.delivery.line.match"
    _inherit = ["mixin.order.line.stock.match"]
    _description = "Sales Order Line & Delivery Move Matching"
    _auto = False
    _order = "product_id, move_id, order_line_id"

    _order_line_table = "sale_order_line"
    _order_table = "sale_order"
    _link_column = "sale_line_id"
    _move_usage = "customer"
    _move_usage_side = "destination"

    order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sales Order Line",
        readonly=True,
    )
    order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        readonly=True,
    )

    def _get_no_order_line_message(self):
        return self.env._(
            "You must select at least one Sales Order line to match or deliver."
        )

    def _get_no_move_message(self):
        return self.env._("You must select at least one delivery move to match.")

    def _select_order_line_date(self):
        return SQL("o.date_commitment")

    def _action_create_moves_from_order_lines(self, order_lines):
        order_lines._action_launch_stock_rule()
        return order_lines.order_id.picking_ids._get_records_action()
