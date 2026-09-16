from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(
        min_display_digits="Product Price",
        compute="_compute_margins",
        store=True,
        groups="base.group_user",
    )
    margin_percent = fields.Float(
        string="Margin (%)",
        compute="_compute_margins",
        store=True,
        aggregator="avg",
        groups="base.group_user",
    )
    purchase_price = fields.Float(
        string="Cost",
        min_display_digits="Product Price",
        compute="_compute_purchase_price",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        groups="base.group_user",
    )

    @api.depends("product_id", "company_id", "currency_id", "product_uom_id")
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id or line.product_type == "combo":
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)

            product_cost = line.product_id.uom_id._get_price_in_unit(
                line.product_id.standard_price,
                line.product_uom_id,
            )

            line.purchase_price = line._convert_to_sol_currency(
                product_cost, line.product_id.cost_currency_id
            )
            _debug.logic(
                "line_cost", line=line, standard=product_cost, cost=line.purchase_price
            )

    @api.depends(
        "price_subtotal",
        "price_unit",
        "product_qty",
        "purchase_price",
        "qty_transferred",
    )
    def _compute_margins(self):
        for line in self:
            _debug.logic(
                "margin_basis",
                line=line,
                by="delivered"
                if line.qty_transferred and not line.product_qty
                else "ordered",
            )
            if line.qty_transferred and not line.product_qty:
                calculated_subtotal = line.price_unit * line.qty_transferred
                line.margin = calculated_subtotal - (
                    line.purchase_price * line.qty_transferred
                )
                line.margin_percent = (
                    calculated_subtotal and line.margin / calculated_subtotal
                )
            else:
                line.margin = line.price_subtotal - (
                    line.purchase_price * line.product_qty
                )
                line.margin_percent = (
                    line.price_subtotal and line.margin / line.price_subtotal
                )
