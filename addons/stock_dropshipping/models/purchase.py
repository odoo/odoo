from odoo import api, fields, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    dropship_picking_count = fields.Integer(
        string="Dropship Count",
        compute="_compute_incoming_transfer_counts",
    )

    @api.depends("picking_ids.is_dropship")
    def _compute_incoming_transfer_counts(self):
        super()._compute_incoming_transfer_counts()
        for order in self:
            dropship_count = len(order.picking_ids.filtered(lambda p: p.is_dropship))
            order.count_transfer_incoming -= dropship_count
            order.dropship_picking_count = dropship_count

    def action_view_picking(self):
        return self._get_action_view_picking(
            self.picking_ids.filtered(lambda p: not p.is_dropship)
        )

    def action_view_dropship(self):
        return self._get_action_view_picking(
            self.picking_ids.filtered(lambda p: p.is_dropship)
        )

    def _prepare_reference_vals(self):
        res = super()._prepare_reference_vals()
        sale_orders = self.line_ids.sale_order_id
        if len(sale_orders) == 1:
            res["sale_ids"] = [Command.link(sale_orders.id)]
        return res

    def _is_dropshipped(self):
        _debug.logic("purchase_is_dropshipped", orders=self)
        self.check_singleton()
        return self.picking_type_id and self.picking_type_id.code == "dropship"

    def _is_dest_address_required(self):
        _debug.logic("dropship_dest_address_required", orders=self)
        return super()._is_dest_address_required() or self._is_dropshipped()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _is_dropshipped(self):
        return self.order_id._is_dropshipped()
