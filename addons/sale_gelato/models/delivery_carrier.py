from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.sale_gelato import utils

_debug = DebugLog(__name__)


class ProviderGelato(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("gelato", "Gelato")],
        ondelete={"gelato": "cascade"},
    )
    gelato_shipping_service_type = fields.Selection(
        selection=[("normal", "Standard Delivery"), ("express", "Express Delivery")],
        default="normal",
        required=True,
    )

    def _is_available_for_order(self, order):
        is_gelato_order = any(order.line_ids.product_id.mapped("gelato_product_uid"))
        is_gelato_delivery = self.delivery_type == "gelato"
        if (is_gelato_order and not is_gelato_delivery) or (
            not is_gelato_order and is_gelato_delivery
        ):
            return False
        return super()._is_available_for_order(order)

    def _filtered_available_carriers(self, partner, source):
        available_delivery_methods = super()._filtered_available_carriers(
            partner, source
        )
        if source._name == "sale.order":
            is_gelato_order = any(
                source.line_ids.product_id.mapped("gelato_product_uid")
            )
        elif source._name == "stock.picking":
            is_gelato_order = any(
                source.move_ids.product_id.mapped("gelato_product_uid")
            )
        else:
            _debug.logic("gelato_carriers_refused", reason="bad_source_type")
            raise UserError(_("Invalid source document type"))
        if is_gelato_order:
            return available_delivery_methods.filtered(
                lambda m: m.delivery_type == "gelato"
            )
        else:
            return available_delivery_methods.filtered(
                lambda m: m.delivery_type != "gelato"
            )

    def gelato_rate_shipment(self, order):
        if error_message := order._get_incomplete_address_error():
            return {
                "success": False,
                "price": 0,
                "error_message": error_message,
            }

        payload = {
            "orderReferenceId": order.id,
            "customerReferenceId": f"Odoo Partner #{order.partner_id.id}",
            "currency": order.currency_id.name,
            "allowMultipleQuotes": "true",
            "products": order._gelato_prepare_items_payload(),
            "recipient": order.partner_shipping_id._gelato_prepare_address_payload(),
        }
        try:
            api_key = order.company_id.sudo().gelato_api_key
            order_data = utils.send_request(
                api_key, "order", "v4", "orders:quote", payload=payload
            )
        except UserError as e:
            return {
                "success": False,
                "price": 0,
                "error_message": str(e),
            }

        total_delivery_price = 0
        for quote_data in order_data["quotes"]:
            matching_shipment_method_prices = [
                shipment_method_data["price"]
                for shipment_method_data in quote_data["shipmentMethods"]
                if shipment_method_data["type"] == self.gelato_shipping_service_type
            ]
            if not matching_shipment_method_prices:
                return {
                    "success": False,
                    "price": 0,
                    "error_message": _(
                        "The delivery method is not available for this order."
                    ),
                }
            else:
                total_delivery_price += min(matching_shipment_method_prices)

        return {
            "success": True,
            "price": total_delivery_price,
        }
