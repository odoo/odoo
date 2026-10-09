import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class WooSaleOrderExporterMapper(Component):
    _name = "woo.sale.order.export.mapper"
    _inherit = "woo.export.mapper"
    _apply_on = "woo.sale.order"

    @mapping
    def status(self, record):
        """Mapping for Status"""
        if record.is_final_status:
            raise MappingError(
                _("WooCommerce Sale Order is already in Completed Status.")
            )
        if not self.backend_record.mark_completed:
            raise MappingError(
                _(
                    "Export Delivery Status is Not Allow from WooCommerce"
                    " Backend '%s'.",
                    self.backend_record.name,
                )
            )
        return {"status": "completed"}

    @mapping
    def tracking_number(self, record):
        """Mapping for tracking number"""
        tracking_numbers = []
        if not self.backend_record.tracking_info:
            return {}
        done_pickings = record.picking_ids.filtered(
            lambda picking: picking.picking_type_id.code == "outgoing"
            and picking.state == "done"
            and not picking.woo_return_bind_ids
            and not picking.is_return_stock_picking
        )
        if not done_pickings:
            raise MappingError(_("No delivery orders in 'done' state."))

        for picking in done_pickings:
            if not picking.carrier_tracking_ref:
                raise MappingError(
                    _("Tracking Reference not found in Delivery Order! %s")
                    % picking.name
                )
            tracking_numbers.append({"tracking_number": picking.carrier_tracking_ref})
        return {
            "meta_data": [
                {
                    "key": "_wc_shipment_tracking_items",
                    "value": tracking_numbers,
                }
            ]
        }


class WooSaleOrderBatchExporter(Component):
    _name = "woo.sale.order.batch.exporter"
    _inherit = "woo.exporter"
    _apply_on = ["woo.sale.order"]

    def _after_export(self):
        """Import the transaction lines after checking WooCommerce order status."""
        woo_order_status = self.env["woo.sale.status"].search(
            [("code", "=", "completed"), ("is_final_status", "=", True)], limit=1
        )
        if not woo_order_status:
            raise ValidationError(
                _(
                    "The WooCommerce order status with the code 'completed' is not "
                    "available in Odoo or isn't marked as 'Final Status'."
                )
            )
        pickings = self.binding.odoo_id.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "outgoing"
            and p.state not in ["done", "cancel"]
        )
        if pickings:
            raise ValidationError(
                _(
                    "Not all pickings associated with sale order %s are in 'done' "
                    "or 'cancel' state."
                )
                % self.binding.odoo_id.name
            )
        self.binding.write({"woo_order_status_id": woo_order_status.id})
        self.binding.write({"woo_order_status": "completed"})
        return super(WooSaleOrderBatchExporter, self)._after_export()
