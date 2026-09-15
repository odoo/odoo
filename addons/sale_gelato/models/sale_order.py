import logging
import pprint
from functools import partial, wraps

from odoo import _, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.sale_gelato import const, utils

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def post_commit(func):

    @wraps(func)
    def _post_commit_wrapper(self, *args, **kwargs):
        with self.env.registry.cursor() as cr:
            self = self.with_env(self.env(cr=cr))
            return func(self, *args, **kwargs)

    return _post_commit_wrapper


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prevent_mixing_gelato_and_non_gelato_products(self):
        for order in self:
            gelato_lines = order.line_ids.filtered(
                lambda l: l.product_id.gelato_product_uid
            )
            non_gelato_lines = (order.line_ids - gelato_lines).filtered(
                lambda l: l.product_id.sale_ok and l.product_id.type != "service"
            )
            if gelato_lines and non_gelato_lines:
                _debug.logic(
                    "gelato_mix_refused",
                    order=order,
                    gelato_lines=gelato_lines,
                    other_lines=non_gelato_lines,
                )
                raise ValidationError(
                    _(
                        "You cannot mix Gelato products with non-Gelato products in the same order."
                    )
                )

    def action_view_delivery_wizard(self):
        res = super().action_view_delivery_wizard()

        if not self.env.context.get("carrier_recompute") and any(
            line.product_id.gelato_product_uid for line in self.line_ids
        ):
            gelato_delivery_method = self.env["delivery.carrier"].search(
                [("delivery_type", "=", "gelato")], limit=1
            )
            _debug.logic(
                "gelato_carrier_defaulted", order=self, carrier=gelato_delivery_method
            )
            res["context"]["default_carrier_id"] = gelato_delivery_method.id
        return res

    def action_confirm(self):
        res = super().action_confirm()
        for order in self.filtered(
            lambda o: any(o.line_ids.product_id.mapped("gelato_product_uid"))
        ):
            if message := order._get_incomplete_address_error():
                _debug.logic(
                    "gelato_order_refused", order=order, reason="incomplete_address"
                )
                raise ValidationError(message)
            order._create_order_on_gelato()
        return res

    def _get_incomplete_address_error(self):
        required_address_fields = ["city", "country_id", "email", "name", "street"]
        if self.partner_id.country_id.code not in const.COUNTRIES_WITHOUT_ZIPCODE:
            required_address_fields.append("zip")
        missing_fields = [
            self.partner_id._fields[field_name]
            for field_name in required_address_fields
            if not self.partner_id[field_name]
        ]
        if missing_fields:
            translated_field_names = [
                f._description_string(self.env) for f in missing_fields
            ]
            return _(
                "The following required address fields are missing: %s",
                ", ".join(translated_field_names),
            )
        return None

    def _create_order_on_gelato(self):
        delivery_line = self.line_ids.filtered(
            lambda l: (
                l.is_delivery and l.product_id.default_code in ("normal", "express")
            )
        )
        payload = {
            "orderType": "draft",
            "orderReferenceId": self.id,
            "customerReferenceId": f"Odoo Partner #{self.partner_id.id}",
            "currency": self.currency_id.name,
            "items": self._gelato_prepare_items_payload(),
            "shipmentMethodUid": delivery_line.product_id.default_code or "cheapest",
            "shippingAddress": self.partner_shipping_id._gelato_prepare_address_payload(),
        }
        _debug.pipeline("gelato_order_send", order=self, items=len(payload["items"]))
        try:
            api_key = self.company_id.sudo().gelato_api_key
            data = utils.send_request(api_key, "order", "v4", "orders", payload=payload)

            self.env.cr.postcommit.add(
                partial(self._confirm_order_on_gelato, data["id"])
            )
            self.env.cr.postrollback.add(
                partial(self._remove_order_on_gelato, data["id"])
            )
        except UserError as e:
            _debug.logic("gelato_order_send_failed", order=self, error=str(e))
            raise UserError(
                _(
                    "The order with reference %(order_reference)s was not sent to Gelato.\n"
                    "Reason: %(error_message)s",
                    order_reference=self.display_name,
                    error_message=str(e),
                )
            ) from e

        _logger.info(
            "Notification received from Gelato with data:\n%s", pprint.pformat(data)
        )
        _debug.lifecycle("gelato_order_created", order=self, gelato_id=data["id"])
        self.message_post(
            body=_("The order has been successfully passed on Gelato."),
            author_id=self.env.ref("base.partner_root").id,
        )

    def _gelato_prepare_items_payload(self):
        items_payload = []
        for gelato_line in self.line_ids.filtered(
            lambda l: l.product_id.gelato_product_uid
        ):
            item_data = {
                "itemReferenceId": gelato_line.product_id.id,
                "productUid": gelato_line.product_id.gelato_product_uid,
                "files": [
                    image._gelato_prepare_file_payload()
                    for image in gelato_line.product_id.product_tmpl_id.gelato_image_ids
                ],
                "quantity": int(gelato_line.product_uom_qty),
            }
            items_payload.append(item_data)
        return items_payload

    @post_commit
    def _confirm_order_on_gelato(self, gelato_order_id):
        self.check_singleton()

        _logger.info(
            "Confirmation of Gelato order %s for sales order %s",
            gelato_order_id,
            self.display_name,
        )
        data = None
        try:
            api_key = self.company_id.sudo().gelato_api_key
            payload = {"orderType": "order"}
            data = utils.send_request(
                api_key,
                "order",
                "v4",
                f"orders/{gelato_order_id}",
                payload=payload,
                method="PATCH",
            )
        except UserError:
            _debug.logic("gelato_confirm_failed", order=self, gelato_id=gelato_order_id)
            self.message_post(
                body=self.env._(
                    "Unable to confirm the order %s on Gelato.", gelato_order_id
                ),
                author_id=self.env.ref("base.partner_root").id,
            )
        finally:
            _logger.info(
                "Received confirmation request response for Gelato order %s:\n%s",
                gelato_order_id,
                pprint.pformat(data),
            )

    @post_commit
    def _remove_order_on_gelato(self, gelato_order_id):
        self.check_singleton()

        _logger.info(
            "Deletion of Gelato order %s for sales order %s",
            gelato_order_id,
            self.display_name,
        )
        data = None
        try:
            api_key = self.company_id.sudo().gelato_api_key
            data = utils.send_request(
                api_key, "order", "v4", f"orders/{gelato_order_id}", method="DELETE"
            )
        except UserError:
            _debug.logic("gelato_delete_failed", order=self, gelato_id=gelato_order_id)
            self.message_post(
                body=self.env._(
                    "Unable to delete the order %s on Gelato.", gelato_order_id
                ),
                author_id=self.env.ref("base.partner_root").id,
            )
        finally:
            _logger.info(
                "Received deletion request response for Gelato order %s:\n%s",
                gelato_order_id,
                pprint.pformat(data),
            )
