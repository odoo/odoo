# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Domain
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website_sale.controllers.checkout.cart import Cart


class CustomerPortal(sale_portal.CustomerPortal):
    def _prepare_quotations_domain(self, partner):
        domain = super()._prepare_quotations_domain(partner)
        website = self.env.website
        website_domain = Domain("assigned_website_id", "in", [False, website.id])
        return Domain.AND([domain, website_domain])

    def _prepare_orders_domain(self, partner):
        domain = super()._prepare_orders_domain(partner)
        website = self.env.website
        website_domain = Domain("assigned_website_id", "in", [False, website.id])
        return Domain.AND([domain, website_domain])

    @route()
    def portal_order_page(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            order_sudo = None

        if order_sudo and (website := order_sudo.assigned_website_id):
            request.update_context(website_id=website.id)
            website._force()

        return super().portal_order_page(order_id, access_token=access_token, **kw)

    def _get_payment_values(self, order_sudo, website_id=None, **kwargs):
        """Override of `sale` to inject the `website_id` into the kwargs.

        :param sale.order order_sudo: The sales order being paid.
        :param int website_id: The website on which the order was made, if any, as a `website` id.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The payment-specific values.
        :rtype: dict
        """
        if not website_id:
            if order_sudo.website_id:
                website_id = order_sudo.website_id.id
            elif website := self.env.website:
                website_id = website.id

        return super()._get_payment_values(order_sudo, website_id=website_id, **kwargs)

    @route("/my/orders/reorder", type="jsonrpc", auth="public", website=True)
    def my_orders_reorder(self, order_id, access_token=None):
        """Retrieve reorder content and automatically add products to the cart.

        param int order_id: The ID of the sale order to reorder.
        param str access_token: The access token for the sale order.
        return: Details of the added products.
        rtype: dict
        """
        try:
            sale_order = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        lines_to_reorder = sale_order.order_line.filtered(
            # Skip section headers, deliveries, event tickets, ...
            lambda line: line.with_user(self.env.user).sudo()._is_reorder_allowed()
        )

        if not lines_to_reorder:
            raise ValidationError(self.env._("Nothing can be reordered in this order"))

        Cart_controller = Cart()
        order_sudo = request.cart or self.env.website._create_cart()
        values = {"tracking_info": []}
        for line in lines_to_reorder:
            linked_products = []
            if line.product_id.type == "combo":
                for linked_line in line.linked_line_ids.filtered("combo_item_id"):
                    combination = (
                        linked_line.product_id.product_template_attribute_value_ids
                        | linked_line.product_no_variant_attribute_value_ids
                    )
                    linked_products.append({
                        "product_template_id": linked_line.product_id.product_tmpl_id.id,
                        "product_id": linked_line.product_id.id,
                        "combination": combination.ids,
                        "no_variant_attribute_value_ids": linked_line.product_no_variant_attribute_value_ids.ids,  # noqa: E501
                        "product_custom_attribute_values": [
                            {
                                "custom_product_template_attribute_value_id": pcav.custom_product_template_attribute_value_id.id,  # noqa: E501
                                "custom_value": pcav.custom_value,
                            }
                            for pcav in linked_line.product_custom_attribute_value_ids
                        ],
                        "quantity": linked_line.product_uom_qty,
                        "combo_item_id": linked_line.combo_item_id.id,
                        "parent_product_template_id": line.product_id.product_tmpl_id.id,
                    })

            cart_values = Cart_controller.add_to_cart(
                product_id=line.product_id.id,
                product_template_id=line.product_id.product_tmpl_id.id,
                quantity=line.product_uom_qty,
                product_custom_attribute_values=[
                    {
                        "custom_product_template_attribute_value_id": pcav.custom_product_template_attribute_value_id.id,  # noqa: E501
                        "custom_value": pcav.custom_value,
                    }
                    for pcav in line.product_custom_attribute_value_ids
                ],
                no_variant_attribute_value_ids=line.product_no_variant_attribute_value_ids.ids,
                linked_products=linked_products,
            )

            values["tracking_info"].extend(cart_values["tracking_info"])

        values["cart_quantity"] = order_sudo.cart_quantity
        values["currency"] = order_sudo.currency_id.name
        return values
