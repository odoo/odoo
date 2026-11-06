import logging

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class WooStockPickingRefundExporterMapper(Component):
    _name = "woo.stock.picking.refund.export.mapper"
    _inherit = "woo.export.mapper"
    _apply_on = "woo.stock.picking.refund"

    @mapping
    def quantity_and_amount(self, record):
        """Mapping for Quantity and Amount"""
        line_items = []
        total_amount = 0.00
        sale_order_products = {
            order_line.product_id.id for order_line in record.sale_id.order_line
        }
        for move in record.move_ids:
            if move.product_id.id not in sale_order_products:
                continue
            order_line = next(
                (
                    order_line
                    for order_line in record.sale_id.order_line
                    if order_line.product_id.id == move.product_id.id
                ),
                None,
            )
            if not order_line:
                continue
            quantity_done = move.quantity_done
            order_line_binding = order_line.woo_bind_ids[0]
            price_unit = float(order_line_binding.price_unit)
            total_tax_line = float(order_line_binding.total_tax_line)

            if quantity_done > order_line_binding.product_uom_qty:
                raise MappingError(
                    _(
                        "Quantity done of move line is greater than quantity in "
                        "WooCommerce Product Quantity."
                    )
                )

            divided_tax = total_tax_line / order_line_binding.product_uom_qty

            list_item = {
                "id": order_line_binding.external_id,
                "quantity": quantity_done,
                "refund_total": price_unit * quantity_done,
                "refund_tax": [
                    {
                        "id": str(move.id),
                        "refund_total": divided_tax * quantity_done,
                    }
                ],
            }
            total_amount += (price_unit + divided_tax) * quantity_done
            line_items.append(list_item)
        return_reason_text = html2plaintext(record.return_reason or "")
        return_data = {
            "order_id": record.sale_id.woo_bind_ids[0].external_id,
            "amount": str(total_amount),
            "line_items": line_items,
            "api_refund": False,
        }
        if return_reason_text:
            return_data["reason"] = return_reason_text
        return return_data


class WooStockPickingRefundBatchExporter(Component):
    _name = "woo.stock.picking.refund.batch.exporter"
    _inherit = "woo.exporter"
    _apply_on = ["woo.stock.picking.refund"]
    _default_binding_field = "woo_return_bind_ids"

    def _after_export(self):
        """Update the Woocommerce status as Refunded of sale order."""
        if not self.binding.sale_id.is_fully_returned:
            return super(WooStockPickingRefundBatchExporter, self)._after_export()
        woo_order_status = self.env["woo.sale.status"].search(
            [("code", "=", "refunded"), ("is_final_status", "=", False)], limit=1
        )
        if not woo_order_status:
            raise ValidationError(
                _(
                    "The WooCommerce order status with the code 'refunded' is not "
                    "available in Odoo."
                )
            )
        self.binding.sale_id.write({"woo_order_status_id": woo_order_status.id})
