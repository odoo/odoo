from odoo import fields, models
from odoo.tools import SQL


class PurchaseReceiptLineMatch(models.Model):
    _name = "purchase.receipt.line.match"
    _inherit = ["mixin.order.line.stock.match"]
    _description = "Purchase Order Line & Receipt Move Matching"
    _auto = False
    _order = "product_id, move_id, order_line_id"

    _order_line_table = "purchase_order_line"
    _order_table = "purchase_order"
    _link_column = "purchase_line_id"
    _move_usage = "supplier"
    _move_usage_side = "source"
    _date_expected_field = "date_commitment"

    order_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Purchase Order Line",
        readonly=True,
    )
    order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        readonly=True,
    )

    def _get_no_order_line_message(self):
        return self.env._(
            "You must select at least one Purchase Order line to match or receive."
        )

    def _get_no_move_message(self):
        return self.env._("You must select at least one receipt move to match.")

    def _get_location_rank(self, order_line, move):
        if order_line.location_final_id and order_line.location_final_id == (
            move.location_final_id
        ):
            return 0
        return 1

    def _select_order_line_date(self):
        return SQL("ol.date_commitment")

    def _action_create_moves_from_order_lines(self, order_lines):
        orders = order_lines.order_id
        orders._create_picking()
        return orders.picking_ids._get_records_action()
