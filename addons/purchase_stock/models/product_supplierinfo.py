from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import formatLang


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    last_purchase_date = fields.Date(
        string="Last Purchase",
        compute="_compute_last_purchase_date",
    )
    show_set_supplier_button = fields.Boolean(
        string="Show Set Supplier Button",
        compute="_compute_show_set_supplier_button",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_last_purchase_date(self):
        self.last_purchase_date = False
        purchases = self.env["purchase.order"].search(
            [
                ("state", "=", "done"),
                (
                    "line_ids.product_id",
                    "in",
                    self.product_tmpl_id.product_variant_ids.ids,
                ),
                ("partner_id", "in", self.partner_id.ids),
            ],
            order="date_order desc",
        )
        for supplier in self:
            products = supplier.product_tmpl_id.product_variant_ids
            for purchase in purchases:
                if purchase.partner_id != supplier.partner_id:
                    continue
                if not (products & purchase.line_ids.product_id):
                    continue
                supplier.last_purchase_date = purchase.date_order
                break

    def _compute_show_set_supplier_button(self):
        self.show_set_supplier_button = True
        orderpoint_id = self.env.context.get(
            "orderpoint_id",
            self.env.context.get("default_orderpoint_id"),
        )
        if orderpoint_id:
            orderpoint = self.env["stock.warehouse.orderpoint"].browse(orderpoint_id)
            self.filtered(
                lambda s: s.id == orderpoint.supplier_id.id,
            ).show_set_supplier_button = False

    @api.depends_context("use_simplified_supplier_name")
    @api.depends("partner_id", "min_qty", "product_uom_id", "currency_id", "price")
    def _compute_display_name(self):
        if self.env.context.get("use_simplified_supplier_name"):
            super()._compute_display_name()
        else:
            for supplier in self:
                price_str = formatLang(
                    self.env,
                    supplier.price,
                    currency_obj=supplier.currency_id,
                )
                supplier.display_name = f"{supplier.partner_id.display_name} ({supplier.min_qty} {supplier.product_uom_id.name} - {price_str})"

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_set_supplier(self):
        self.ensure_one()
        orderpoint_id = self.env.context.get("orderpoint_id")
        if not orderpoint_id:
            return
        orderpoint = self.env["stock.warehouse.orderpoint"].browse(orderpoint_id)
        if "buy" not in orderpoint.route_id.rule_ids.mapped("action"):
            domain = Domain.AND(
                [
                    [("action", "=", "buy")],
                    Domain.OR(
                        [
                            [("company_id", "=", orderpoint.company_id.id)],
                            [("company_id", "=", False)],
                        ],
                    ),
                ],
            )
            orderpoint.route_id = (
                self.env["stock.rule"].search(domain, limit=1).route_id.id
            )
        orderpoint.supplier_id = self
        supplier_min_qty = self.product_uom_id._compute_quantity(
            self.min_qty,
            orderpoint.product_id.uom_id,
        )
        if orderpoint.qty_to_order < supplier_min_qty:
            orderpoint.qty_to_order = supplier_min_qty
        if self.env.context.get("replenish_id"):
            replenish = self.env["product.replenish"].browse(
                self.env.context.get("replenish_id"),
            )
            replenish.supplier_id = self
            return {
                "type": "ir.actions.act_window",
                "name": "Replenish",
                "res_model": "product.replenish",
                "res_id": replenish.id,
                "target": "new",
                "view_mode": "form",
            }
        return orderpoint.action_stock_replenishment_info()
