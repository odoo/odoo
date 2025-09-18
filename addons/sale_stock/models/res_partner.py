from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_line_ids = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="partner_id",
        string="Sale Lines",
    )
    customer_on_time_rate = fields.Float(
        string="Customer On-Time Delivery Rate",
        compute="_compute_customer_on_time_rate",
        help="Over the past x days; the number of products delivered on time to this customer divided by the number of ordered products. "
        "x is either the System Parameter sale_stock.on_time_delivery_days or the default 365",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("sale_line_ids")
    def _compute_customer_on_time_rate(self):
        date_order_days_delta = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "sale_stock.on_time_delivery_days",
                default="365",
            ),
        )
        order_lines = self.env["sale.order.line"].search(
            [
                ("partner_id", "in", self.ids),
                (
                    "order_id.date_order",
                    ">",
                    fields.Date.today() - timedelta(date_order_days_delta),
                ),
                ("qty_transferred", "!=", 0),
                ("order_id.state", "=", "sale"),
                (
                    "product_id",
                    "in",
                    self.env["product.product"]
                    .sudo()
                    ._search([("type", "!=", "service")]),
                ),
            ],
        )
        lines_quantity = defaultdict(lambda: 0)
        moves = self.env["stock.move"].search(
            [("sale_line_id", "in", order_lines.ids), ("state", "=", "done")],
        )
        # Fetch fields from db and put them in cache.
        order_lines.read(["order_id", "partner_id", "product_uom_qty"], load="")
        order_lines.order_id.read(["date_commitment"], load="")
        moves.read(["sale_line_id", "date"], load="")
        moves = moves.filtered(
            lambda m: m.sale_line_id.order_id.date_commitment
            and m.date.date() <= m.sale_line_id.order_id.date_commitment.date(),
        )
        for move, quantity in zip(moves, moves.mapped("quantity")):
            lines_quantity[move.sale_line_id.id] += quantity
        partner_dict = {}
        for line in order_lines:
            on_time, ordered = partner_dict.get(line.partner_id, (0, 0))
            ordered += line.product_uom_qty
            on_time += lines_quantity[line.id]
            partner_dict[line.partner_id] = (on_time, ordered)
        seen_partner = self.env["res.partner"]
        for partner, numbers in partner_dict.items():
            seen_partner |= partner
            on_time, ordered = numbers
            partner.customer_on_time_rate = (
                on_time / ordered * 100 if ordered else -1
            )  # use negative number to indicate no data
        (self - seen_partner).customer_on_time_rate = -1
