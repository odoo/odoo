from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import formatLang

_debug = DebugLog(__name__)


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    date_last_purchase = fields.Date(
        string="Last Purchase",
        compute="_compute_date_last_purchase",
    )
    show_set_supplier_button = fields.Boolean(
        compute="_compute_show_set_supplier_button"
    )

    @api.depends("partner_id", "product_tmpl_id.product_variant_ids")
    def _compute_date_last_purchase(self):
        _debug.perf.count("last_purchase_date_compute", supplierinfos=self)
        self.date_last_purchase = False
        groups = self.env["purchase.order.line"]._read_group(
            [
                ("order_id.state", "=", "done"),
                ("product_id", "in", self.product_tmpl_id.product_variant_ids.ids),
                ("partner_id", "in", self.partner_id.ids),
            ],
            ["partner_id", "product_id"],
            ["date_order:max"],
        )
        last_by_key = {
            (partner.id, product.id): date_order
            for partner, product, date_order in groups
        }
        for supplier in self:
            dates = [
                last_by_key[(supplier.partner_id.id, product.id)]
                for product in supplier.product_tmpl_id.product_variant_ids
                if (supplier.partner_id.id, product.id) in last_by_key
            ]
            supplier.date_last_purchase = max(dates) if dates else False

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

    def action_set_supplier(self):
        _debug.lifecycle("supplier_set", supplierinfos=self)
        self.check_singleton()
        orderpoint_id = self.env.context.get("orderpoint_id")
        if not orderpoint_id:
            return None
        orderpoint = self.env["stock.warehouse.orderpoint"].browse(orderpoint_id)
        if not orderpoint.route_id._has_buy_rule():
            domain = Domain("action", "=", "buy") & Domain.OR(
                [
                    Domain("company_id", "=", orderpoint.company_id.id),
                    Domain("company_id", "=", False),
                ],
            )
            orderpoint.route_id = (
                self.env["stock.rule"].search(domain, limit=1).route_id.id
            )
        orderpoint.supplier_id = self
        supplier_min_qty = self.product_uom_id._get_quantity_estimate(
            self.min_qty,
            orderpoint.product_id.uom_id,
        )
        orderpoint.qty_to_order = max(orderpoint.qty_to_order, supplier_min_qty)
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
