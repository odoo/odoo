from odoo import Command, api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends("reference_ids", "reference_ids.sale_ids")
    def _compute_sale_orders(self):
        super()._compute_sale_orders()

    @api.depends("line_ids.sale_order_id.partner_shipping_id")
    def _compute_dest_address_id(self):
        super()._compute_dest_address_id()
        for order in self:
            if not order._is_dest_address_required():
                continue
            shipping_addresses = order._get_sale_orders().partner_shipping_id
            _debug.logic(
                "dest_address_from_sale_orders",
                order=order,
                addresses=shipping_addresses,
                applied=len(shipping_addresses) == 1,
            )
            if len(shipping_addresses) == 1:
                order.dest_address_id = shipping_addresses

    def _is_dest_address_required(self):
        self.check_singleton()
        return bool(self.dest_address_id)

    def _get_sale_orders(self):
        return super()._get_sale_orders() | self.reference_ids.sale_ids


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_stock_move_vals_list(self, picking):
        res = super()._prepare_stock_move_vals_list(picking)
        _debug.pipeline(
            "move_vals_from_purchase_line",
            line=self,
            picking=picking,
            moves=len(res),
            sale_line=self.sale_line_id,
        )
        for re in res:
            if self.sale_line_id and re.get("location_final_id"):
                final_loc = self.env["stock.location"].browse(
                    re.get("location_final_id")
                )
                _debug.logic(
                    "move_sale_line_link",
                    line=self,
                    location=final_loc,
                    usage=final_loc.usage,
                    linked=final_loc.usage in {"customer", "transit"},
                )
                if final_loc.usage in {"customer", "transit"}:
                    re["sale_line_id"] = self.sale_line_id.id
            if self.sale_line_id.route_ids:
                re["route_ids"] = [
                    Command.link(route_id)
                    for route_id in self.sale_line_id.route_ids.ids
                ]
        return res

    def _get_sale_order_line_product(self):
        return self.sale_line_id.product_id

    def _get_candidate(
        self,
        product_id,
        product_qty,
        product_uom_id,
        location_id,
        name,
        origin,
        company_id,
        values,
    ):
        if not values.get("move_dest_ids") and values.get("sale_line_id"):
            lines = self.filtered(
                lambda po_line: po_line.sale_line_id.id == values["sale_line_id"]
            )
            _debug.logic(
                "candidate_line_narrowed",
                candidates=len(self),
                matching=len(lines),
                sale_line=values["sale_line_id"],
            )
            return super(PurchaseOrderLine, lines)._get_candidate(
                product_id,
                product_qty,
                product_uom_id,
                location_id,
                name,
                origin,
                company_id,
                values,
            )
        return super()._get_candidate(
            product_id,
            product_qty,
            product_uom_id,
            location_id,
            name,
            origin,
            company_id,
            values,
        )

    @api.model
    def _prepare_purchase_order_line_from_procurement(
        self,
        product_id,
        product_qty,
        product_uom_id,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        po,
    ):
        res = super()._prepare_purchase_order_line_from_procurement(
            product_id,
            product_qty,
            product_uom_id,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            po,
        )
        _debug.logic(
            "procurement_line_sale_link",
            product=product_id,
            sale_line=values.get("sale_line_id", False),
            linked=not values.get("move_dest_ids"),
        )
        if not values.get("move_dest_ids"):
            res["sale_line_id"] = values.get("sale_line_id", False)
        return res
