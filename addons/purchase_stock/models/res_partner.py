from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    purchase_line_ids = fields.One2many(
        comodel_name="purchase.order.line",
        inverse_name="partner_id",
        string="Purchase Lines",
    )
    on_time_rate = fields.Float(
        string="On-Time Delivery Rate",
        compute="_compute_on_time_rate",
        groups="purchase.group_purchase_user",
        help="Over the past x days; the number of products received on time divided by the number of ordered products."
        "x is either the System Parameter purchase_stock.on_time_delivery_days or the default 365",
    )
    suggest_based_on = fields.Char(default="30_days")
    suggest_days = fields.Integer(default=7)
    suggest_percent = fields.Integer(default=100)
    group_rfq = fields.Selection(
        selection=[
            ("default", "On Order"),
            ("day", "Daily"),
            ("week", "Weekly"),
            ("all", "Always"),
        ],
        string="Group RFQ",
        default="default",
        required=True,
        help="Define if RFQ should be grouped \
        together based on expected arrival, except for dropship operations.\n \
        On Order: Replenishment needs will be grouped together except for MTO.\n \
        Daily: Replenishment needs will be grouped if the expected arrival is the same day\n \
        Weekly: Replenishment needs will be grouped if the expected arrival is the same week or week day\n \
        Always: Replenishment needs will always be grouped.",
    )
    group_on = fields.Selection(
        selection=[
            ("default", "Expected Date"),
            ("1", "Monday"),
            ("2", "Tuesday"),
            ("3", "Wednesday"),
            ("4", "Thursday"),
            ("5", "Friday"),
            ("6", "Saturday"),
            ("7", "Sunday"),
        ],
        string="Week Day",
        default="default",
        required=True,
    )

    @api.depends("purchase_line_ids")
    def _compute_on_time_rate(self):
        _debug.perf.count("on_time_rate_compute", partners=self)
        date_order_days_delta = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("purchase_stock.on_time_delivery_days", default="365"),
        )
        order_lines = self.env["purchase.order.line"].search(
            [
                ("partner_id", "in", self.ids),
                (
                    "date_order",
                    ">",
                    fields.Date.today() - timedelta(date_order_days_delta),
                ),
                ("qty_transferred", "!=", 0),
                ("order_id.state", "=", "done"),
                ("date_commitment", "!=", False),
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
            [("purchase_line_id", "in", order_lines.ids), ("state", "=", "done")],
        )
        order_lines.fetch(["date_commitment", "partner_id", "product_uom_qty"])
        moves.fetch(["purchase_line_id", "date", "quantity", "location_id"])
        moves = moves.filtered(
            lambda m: (
                m.location_id._is_incoming()
                and m.date.date() <= m.purchase_line_id.date_commitment.date()
            ),
        )
        for move in moves:
            lines_quantity[move.purchase_line_id.id] += move.quantity
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
            partner.on_time_rate = on_time / ordered * 100 if ordered else -1
        (self - seen_partner).on_time_rate = -1
