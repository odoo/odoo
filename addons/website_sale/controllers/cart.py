from werkzeug.exceptions import NotFound

from odoo import fields
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq
from odoo.tools.image import image_data_uri
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale

_debug = DebugLog(__name__)


class Cart(PaymentPortal):
    @route(route="/shop/cart", type="http", auth="public", website=True, sitemap=False)
    def cart(self, id=None, access_token=None, revive_method="", **post):
        if not request.website.has_ecommerce_access():
            _debug.logic("cart_refused", reason="no_ecommerce_access")
            return request.redirect("/web/login")

        order_sudo = request.cart

        values = {}
        if id and access_token:
            abandoned_order = request.env["sale.order"].sudo().browse(int(id)).exists()
            if not abandoned_order or not consteq(
                abandoned_order.access_token, access_token
            ):
                _debug.logic(
                    "abandoned_cart_refused", reason="bad_token", order=int(id)
                )
                raise NotFound
            if abandoned_order.state != "draft":
                values.update({"abandoned_proceed": True})
            elif revive_method == "squash" or (
                revive_method == "merge" and not request.session.get("sale_order_id")
            ):
                _debug.lifecycle(
                    "abandoned_cart_revived",
                    by="squash",
                    order=abandoned_order.id,
                )
                request.session["sale_order_id"] = abandoned_order.id
                return request.redirect("/shop/cart")
            elif revive_method == "merge":
                _debug.lifecycle(
                    "abandoned_cart_revived",
                    by="merge",
                    order=abandoned_order.id,
                    lines=len(abandoned_order.line_ids),
                )
                abandoned_order.line_ids.write(
                    {"order_id": request.session["sale_order_id"]}
                )
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session.get("sale_order_id"):
                values.update(
                    {
                        "id": abandoned_order.id,
                        "access_token": abandoned_order.access_token,
                    }
                )

        values.update(
            {
                "website_sale_order": order_sudo,
                "date": fields.Date.today(),
                "suggested_products": [],
            }
        )
        if order_sudo:
            inactive_lines = order_sudo.line_ids.filtered(
                lambda sol: sol.product_id and not sol.product_id.active
            )
            _debug.lifecycle(
                "cart_inactive_lines_dropped",
                order=order_sudo.id,
                lines=inactive_lines,
            )
            inactive_lines.unlink()
            values["suggested_products"] = order_sudo._cart_accessories()
            values.update(self._get_express_shop_payment_values(order_sudo))

        values.update(request.website._get_checkout_step_values())
        values.update(self._cart_values(**post))
        values.update(self._prepare_order_history())
        return request.render("website_sale.cart", values)

    def _cart_values(self, **post):
        return {}

    def _cart_add_linked_product(self, order_sudo, product_data, line_ids, kwargs):
        product_sudo = (
            request.env["product.product"]
            .sudo()
            .browse(product_data["product_id"])
            .exists()
        )
        if product_data["quantity"] and (
            not product_sudo
            or (
                not product_sudo._is_add_to_cart_allowed()
                and not product_data.get("combo_item_id")
            )
        ):
            _debug.logic(
                "add_to_cart_refused",
                reason="linked_product_not_addable",
                product=product_data["product_id"],
            )
            raise UserError(
                _(
                    "The given product does not exist therefore it cannot be added to cart."
                )
            )

        _debug.lifecycle(
            "add_linked_product_to_cart",
            order=order_sudo.id,
            product=product_data["product_id"],
            quantity=product_data["quantity"],
        )
        return order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=product_data["product_id"],
            quantity=product_data["quantity"],
            uom_id=product_data.get("uom_id"),
            product_custom_attribute_values=product_data[
                "product_custom_attribute_values"
            ],
            no_variant_attribute_value_ids=[
                int(value_id)
                for value_id in product_data["no_variant_attribute_value_ids"]
            ],
            linked_line_id=line_ids[product_data["parent_product_template_id"]],
            **self._get_additional_cart_update_values(product_data),
            **kwargs,
        )

    @route(
        route="/shop/cart/add",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        sitemap=False,
    )
    def add_to_cart(
        self,
        product_template_id,
        product_id,
        quantity=1.0,
        uom_id=None,
        product_custom_attribute_values=None,
        no_variant_attribute_value_ids=None,
        linked_products=None,
        **kwargs,
    ):
        order_sudo = request.cart or request.website._create_cart()
        quantity = int(quantity)

        product = request.env["product.product"].browse(product_id).exists()
        if not product or not product._is_add_to_cart_allowed():
            _debug.logic(
                "add_to_cart_refused",
                reason="product_not_addable",
                product=product_id,
                order=order_sudo.id,
            )
            raise UserError(
                _(
                    "The given product does not exist therefore it cannot be added to cart."
                )
            )

        added_qty_per_line = {}
        values = order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=product_id,
            quantity=quantity,
            uom_id=uom_id,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs,
        )
        _debug.lifecycle(
            "add_to_cart",
            order=order_sudo.id,
            product=product_id,
            quantity=quantity,
            line=values["line_id"],
            added=values["added_qty"],
        )
        line_ids = {product_template_id: values["line_id"]}
        added_qty_per_line[values["line_id"]] = values["added_qty"]
        is_combo = product.type == "combo"
        updated_line = (
            values["line_id"]
            and order_sudo.line_ids.filtered(lambda line: line.id == values["line_id"])
        ) or order_sudo.env["sale.order.line"]

        if linked_products and values["line_id"]:
            for product_data in linked_products:
                product_values = self._cart_add_linked_product(
                    order_sudo, product_data, line_ids, kwargs
                )
                if is_combo and not product_values.get("quantity"):
                    _debug.logic(
                        "combo_rolled_back",
                        order=order_sudo.id,
                        line=updated_line.id,
                    )
                    updated_line.unlink()
                    return {
                        "cart_quantity": order_sudo.cart_quantity,
                        "notification_info": {
                            "warning": product_values.get("warning", ""),
                        },
                        "quantity": 0,
                        "tracking_info": [],
                    }

                line_ids[product_data["product_template_id"]] = product_values[
                    "line_id"
                ]
                added_qty_per_line[product_values["line_id"]] = product_values[
                    "added_qty"
                ]

        warning = values.pop("warning", "")
        if is_combo and order_sudo._check_combo_quantities(updated_line):
            added_qty_per_line = {
                line.id: updated_line.product_qty
                for line in (updated_line + updated_line.linked_line_ids)
            }
            warning = updated_line.shop_warning
            values["quantity"] = updated_line.product_qty

        order_sudo._sync_cart_after_update()

        if updated_line.product_type == "combo":
            updated_line._check_validity()

        positive_added_qty_per_line = {
            line_id: qty for line_id, qty in added_qty_per_line.items() if qty > 0
        }

        return {
            "cart_quantity": order_sudo.cart_quantity,
            "notification_info": {
                **self._get_cart_notification_information(
                    order_sudo, positive_added_qty_per_line
                ),
                "warning": warning,
            },
            "quantity": values.pop("quantity", 0),
            "tracking_info": self._get_tracking_information(
                order_sudo, line_ids.values()
            ),
        }

    @route(
        route="/shop/cart/quick_add",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def quick_add(self, product_template_id, product_id, quantity=1.0, **kwargs):
        values = self.add_to_cart(
            product_template_id, product_id, quantity=quantity, **kwargs
        )

        IrUiView = request.env["ir.ui.view"]
        order_sudo = request.cart
        values["website_sale.cart_lines"] = IrUiView._render_template(
            "website_sale.cart_lines",
            {
                "website_sale_order": order_sudo,
                "date": fields.Date.today(),
                "suggested_products": order_sudo._cart_accessories(),
            },
        )
        values["website_sale.shorter_cart_summary"] = IrUiView._render_template(
            "website_sale.shorter_cart_summary",
            {
                "website_sale_order": order_sudo,
                "show_shorter_cart_summary": True,
                **self._get_express_shop_payment_values(order_sudo),
                **request.website._get_checkout_step_values(),
            },
        )
        values["website_sale.quick_reorder_history"] = IrUiView._render_template(
            "website_sale.quick_reorder_history",
            {
                "website_sale_order": order_sudo,
                **self._prepare_order_history(),
            },
        )
        values["cart_ready"] = order_sudo._is_cart_ready()
        return values

    def _get_express_shop_payment_values(self, order, **kwargs):
        payment_form_values = CustomerPortal._prepare_payment_form_context(
            self, order, website_id=request.website.id, is_express_checkout=True
        )
        payment_form_values.update(
            {
                "payment_access_token": payment_form_values.pop("access_token"),
                "minor_amount": payment_utils.major_to_minor_currency_units(
                    order._get_amount_total_excluding_delivery(), order.currency_id
                ),
                "merchant_name": request.website.name,
                "transaction_route": f"/shop/payment/transaction/{order.id}",
                "express_checkout_route": WebsiteSale._express_checkout_route,
                "landing_route": "/shop/payment/validate",
                "payment_method_unknown_id": request.env.ref(
                    "payment.payment_method_unknown"
                ).id,
                "shipping_info_required": order._has_deliverable_products(),
                "delivery_amount": payment_utils.major_to_minor_currency_units(
                    order.amount_total - order._get_amount_total_without_delivery(),
                    order.currency_id,
                ),
                "shipping_address_update_route": WebsiteSale._express_checkout_delivery_route,
            }
        )
        if request.website.is_public_user():
            payment_form_values["partner_id"] = -1
        return payment_form_values

    @route(
        route="/shop/cart/update",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        sitemap=False,
    )
    def update_cart(self, line_id, quantity, product_id=None, **kwargs):
        order_sudo = request.cart
        quantity = int(quantity)
        IrUiView = request.env["ir.ui.view"]

        if not line_id:
            line_id = order_sudo.line_ids.filtered(
                lambda sol: sol.product_id.id == product_id
            )[:1].id

        values = order_sudo._cart_update_line_quantity(line_id, quantity, **kwargs)
        _debug.lifecycle(
            "update_cart",
            order=order_sudo.id,
            line=line_id,
            quantity=quantity,
            product=product_id,
        )

        values["cart_quantity"] = order_sudo.cart_quantity
        values["cart_ready"] = order_sudo._is_cart_ready()
        values["amount"] = order_sudo.amount_total
        values["minor_amount"] = (
            order_sudo
            and payment_utils.major_to_minor_currency_units(
                order_sudo.amount_total, order_sudo.currency_id
            )
        ) or 0.0
        values["website_sale.cart_lines"] = IrUiView._render_template(
            "website_sale.cart_lines",
            {
                "website_sale_order": order_sudo,
                "date": fields.Date.today(),
                "suggested_products": order_sudo._cart_accessories(),
            },
        )
        values["website_sale.total"] = IrUiView._render_template(
            "website_sale.total",
            {
                "website_sale_order": order_sudo,
            },
        )
        values["website_sale.quick_reorder_history"] = IrUiView._render_template(
            "website_sale.quick_reorder_history",
            {
                "website_sale_order": order_sudo,
                **self._prepare_order_history(),
            },
        )
        return values

    def _prepare_order_history(self):

        def is_same_combo(line1_, line2_):
            return (
                line1_.linked_line_ids.product_id.ids
                == line2_.linked_line_ids.product_id.ids
            )

        previous_orders_lines_sudo = (
            request.env["sale.order"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", request.env.user.partner_id.id),
                    ("state", "=", "done"),
                    ("website_id", "=", request.website.id),
                ],
                order="date_order desc",
                limit=10,
            )
            .line_ids
        )

        SaleOrderLineSudo = request.env["sale.order.line"].sudo()
        cart_lines_sudo = request.cart.line_ids if request.cart else SaleOrderLineSudo
        seen_lines_sudo = SaleOrderLineSudo
        lines_per_order_date = {}
        for line_sudo in previous_orders_lines_sudo:
            product_id = line_sudo.product_id.id
            if (
                line_sudo.linked_line_id.product_type == "combo"
                or not line_sudo._is_sellable()
                or (
                    request.website.prevent_zero_price_sale
                    and line_sudo.product_id._get_combination_info_variant()["price"]
                    == 0
                )
            ):
                continue

            is_combo = line_sudo.product_type == "combo"
            if any(
                l.product_id.id == product_id
                and (not is_combo or is_same_combo(line_sudo, l))
                for l in cart_lines_sudo + seen_lines_sudo
            ):
                continue
            seen_lines_sudo |= line_sudo

            days_ago = (fields.Date.today() - line_sudo.order_id.date_order.date()).days
            if days_ago == 0:
                line_group_label = self.env._("Today")
            elif days_ago == 1:
                line_group_label = self.env._("Yesterday")
            else:
                line_group_label = self.env._("%s days ago", days_ago)
            lines_per_order_date.setdefault(line_group_label, SaleOrderLineSudo)
            lines_per_order_date[line_group_label] |= line_sudo

        return {
            "order_history": [
                {"label": label, "lines": lines}
                for label, lines in lines_per_order_date.items()
            ]
        }

    @route(
        route="/shop/cart/quantity",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_quantity(self):
        if "website_sale_cart_quantity" not in request.session:
            return request.cart.cart_quantity
        return request.session["website_sale_cart_quantity"]

    @route(route="/shop/cart/clear", type="jsonrpc", auth="public", website=True)
    def clear_cart(self):
        _debug.lifecycle(
            "clear_cart",
            order=request.cart.id,
            lines=len(request.cart.line_ids),
        )
        request.cart.line_ids.unlink()

    def _get_cart_notification_information(self, order, added_qty_per_line):
        lines = order.line_ids.filtered(lambda line: line.id in set(added_qty_per_line))
        if not lines:
            _debug.logic("cart_notification_skipped", reason="no_lines", order=order.id)
            return {}

        return {
            "currency_id": order.currency_id.id,
            "lines": [
                {
                    "id": line.id,
                    "image_url": order.website_id.image_url(
                        line.product_id, "image_128"
                    ),
                    "quantity": added_qty_per_line[line.id],
                    "name": line._get_line_header(),
                    "combination_name": line._get_combination_name(),
                    "description": line._get_line_multiline_description_variants(),
                    "price_total": (
                        line._get_displayed_unit_price() * added_qty_per_line[line.id]
                    ),
                    **self._get_additional_cart_notification_information(line),
                }
                for line in lines
            ],
        }

    def _get_tracking_information(self, order_sudo, line_ids):
        lines = order_sudo.line_ids.filtered(
            lambda line: line.id in line_ids
        ).with_context(display_default_code=False)
        return [
            {
                "item_id": line.product_id.barcode or line.product_id.id,
                "item_name": line.product_id.display_name,
                "item_category": line.product_id.categ_id.name,
                "currency": line.currency_id.name,
                "price": line.price_unit_discounted_taxexc,
                "discount": line.price_unit - line.price_unit_discounted_taxexc,
                "quantity": line.product_qty,
            }
            for line in lines
        ]

    def _get_additional_cart_update_values(self, data):
        if data.get("combo_item_id"):
            return {"combo_item_id": data["combo_item_id"]}
        return {}

    def _get_additional_cart_notification_information(self, line):
        infos = {}
        if combo_item := line.combo_item_id:
            infos["linked_line_id"] = line.linked_line_id.id
            if (
                not combo_item.product_id.sudo(False).has_access("read")
                and combo_item.product_id.image_128
            ):
                infos["image_url"] = image_data_uri(combo_item.product_id.image_128)

        if line.product_template_id._has_multiple_uoms():
            infos["uom_name"] = line.product_uom_id.name

        return infos
