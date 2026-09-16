from odoo import api, fields, models
from odoo.http import request
from odoo.tools import float_round
from odoo.tools.translate import html_translate

from odoo.addons.website.models import ir_http


class ProductTemplate(models.Model):
    _inherit = "product.template"

    allow_out_of_stock_order = fields.Boolean(
        string="Sell when Out-of-Stock",
        default=True,
    )

    available_threshold = fields.Float(
        string="Show Threshold",
        default=5.0,
    )
    show_availability = fields.Boolean(
        string="Show availability Qty",
        default=False,
    )
    out_of_stock_message = fields.Html(
        string="Out-of-Stock Message",
        translate=html_translate,
    )

    def _is_sold_out(self):
        if not self.is_storable or self.allow_out_of_stock_order:
            return False
        return self.product_variant_id._is_sold_out()

    def _website_show_quick_add(self):
        return super()._website_show_quick_add() and not self._is_sold_out()

    def _get_additionnal_combination_info(
        self, product_or_template, quantity, uom, date, website
    ):
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, uom, date, website
        )

        if not self.env.context.get("website_sale_stock_get_quantity"):
            return res

        if product_or_template.type == "combo":
            max_quantities = [
                max_quantity
                for combo in product_or_template.sudo().combo_ids
                if (max_quantity := combo._get_max_quantity(website, request.cart))
                is not None
            ]
            if max_quantities:
                res["max_combo_quantity"] = min(max_quantities)

        if not product_or_template.is_storable:
            return res

        res.update(
            {
                "is_storable": True,
                "allow_out_of_stock_order": product_or_template.allow_out_of_stock_order,
                "available_threshold": product_or_template.available_threshold,
            }
        )
        if product_or_template.is_product_variant:
            product_sudo = product_or_template.sudo()
            computed_qty = product_sudo.uom_id._get_quantity_in_unit(
                website._get_product_available_qty(product_sudo),
                to_unit=uom,
                round=False,
            )
            qty_free = float_round(
                computed_qty, precision_digits=0, rounding_method="DOWN"
            )
            has_stock_notification = product_sudo._has_stock_notification(
                self.env.user.partner_id
            ) or (
                request
                and product_sudo.id
                in request.session.get("product_with_stock_notification_enabled", set())
            )
            stock_notification_email = request and request.session.get(
                "stock_notification_email", ""
            )
            cart_quantity = 0.0
            if not product_sudo.allow_out_of_stock_order:
                cart_quantity = product_sudo.uom_id._get_quantity_in_unit(
                    request.cart._get_cart_qty(product_sudo.id),
                    to_unit=uom,
                )
            res.update(
                {
                    "qty_free": qty_free,
                    "cart_qty": cart_quantity,
                    "uom_name": uom.name,
                    "uom_rounding": uom.rounding,
                    "show_availability": product_sudo.show_availability,
                    "out_of_stock_message": product_sudo.out_of_stock_message,
                    "has_stock_notification": has_stock_notification,
                    "stock_notification_email": stock_notification_email,
                }
            )
        else:
            res.update(
                {
                    "qty_free": 0,
                    "cart_qty": 0,
                }
            )

        return res

    @api.model
    def _get_additional_configurator_data(
        self, product_or_template, date, currency, pricelist, *, uom=None, **kwargs
    ):
        data = super()._get_additional_configurator_data(
            product_or_template, date, currency, pricelist, **kwargs
        )

        if (
            website := ir_http.get_request_website()
        ) and product_or_template.is_product_variant:
            max_quantity = product_or_template._get_max_quantity(
                website, request.cart, **kwargs
            )
            if max_quantity is not None:
                if uom:
                    max_quantity = product_or_template.uom_id._get_quantity_in_unit(
                        max_quantity, to_unit=uom
                    )
                data["qty_free"] = max_quantity
        return data
