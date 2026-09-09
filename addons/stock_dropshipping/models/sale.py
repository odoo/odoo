from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    dropship_picking_count = fields.Integer(
        string="Dropship Count",
        compute="_compute_outgoing_transfer_counts",
    )

    @api.depends("picking_ids.is_dropship")
    def _compute_outgoing_transfer_counts(self):
        super()._compute_outgoing_transfer_counts()
        for order in self:
            dropship_count = len(order.picking_ids.filtered(lambda p: p.is_dropship))
            order.count_transfer_outgoing -= dropship_count
            order.dropship_picking_count = dropship_count

    def action_view_picking(self):
        return self._get_action_view_picking(
            self.picking_ids.filtered(lambda p: not p.is_dropship)
        )

    def action_view_dropship(self):
        return self._get_action_view_picking(
            self.picking_ids.filtered(lambda p: p.is_dropship)
        )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_is_mto(self):
        _debug.perf.count("dropship_mto_compute", lines=self)
        super()._compute_is_mto()
        for line in self:
            if not line.display_qty_widget or line.is_mto:
                continue
            product_routes = line.route_ids or (
                line.product_id.route_ids + line.product_id.categ_id.total_route_ids
            )
            for pull_rule in product_routes.mapped("rule_ids"):
                if pull_rule.picking_type_id.sudo().code == "dropship":
                    line.is_mto = True
                    break

    def _get_procurement_qty(self, previous_product_qty=False):
        _debug.logic("dropship_procurement_qty", lines=self)
        purchase_lines_sudo = self.sudo().purchase_line_ids
        if (
            any(
                pol._is_dropshipped() and pol.state != "cancel"
                for pol in purchase_lines_sudo
            )
            and self.product_id == purchase_lines_sudo.product_id
        ):
            qty = 0.0
            for po_line in purchase_lines_sudo.filtered(lambda r: r.state != "cancel"):
                qty += po_line.product_uom_id._get_quantity_in_unit(
                    po_line.product_qty, self.product_uom_id, rounding_method="HALF-UP"
                )
            return qty
        else:
            return super()._get_procurement_qty(
                previous_product_qty=previous_product_qty
            )

    @api.depends("purchase_line_count")
    def _compute_product_readonly(self):
        super()._compute_product_readonly()
        if self.env.user.has_group("purchase.group_purchase_user"):
            for line in self:
                if line.purchase_line_count > 0:
                    line.product_readonly = True

    def _prepare_purchase_service_order_values(self, supplierinfo):
        res = super()._prepare_purchase_service_order_values(supplierinfo)
        dropship_operation = self.env["stock.picking.type"].search(
            [
                ("company_id", "=", res["company_id"]),
                ("code", "=", "dropship"),
            ],
            limit=1,
            order="sequence",
        )
        if dropship_operation:
            res["dest_address_id"] = self.order_id.partner_shipping_id.id
            res["picking_type_id"] = dropship_operation.id
        return res
