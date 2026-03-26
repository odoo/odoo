# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.http import request

from odoo.addons.website.models import ir_http


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website):
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, uom, date, website
        )

        if not self.env.context.get("website_sale_product_page"):
            return res

        if product_or_template.type == "combo":
            # The max quantity of a combo product is the max quantity of its combo with the lowest
            # max quantity. If none of the combos has a max quantity, then the combo product also
            # has no max quantity.
            max_quantities = [
                max_quantity
                for combo in product_or_template.sudo().combo_ids
                if (max_quantity := combo._get_max_quantity(website, request.cart)) is not None
            ]
            if max_quantities:
                # No uom conversion: combo are not supposed to be sold with other uoms.
                res["max_combo_quantity"] = min(max_quantities)

        if product_or_template.is_storable and product_or_template.is_product_variant:
            product_sudo = product_or_template.sudo()
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
            res.update({
                "has_stock_notification": has_stock_notification,
                "stock_notification_email": stock_notification_email,
                "is_in_wishlist": product_sudo._is_in_wishlist(),
            })

        return res

    @api.model
    def _get_additional_configurator_data(
        self, product_or_template, date, currency, pricelist, *, uom=None, **kwargs
    ):
        """Override of `website_sale` to append stock data.

        :param product.product|product.template product_or_template: The product for which to get
            additional data.
        :param datetime date: The date to use to compute prices.
        :param res.currency currency: The currency to use to compute prices.
        :param product.pricelist pricelist: The pricelist to use to compute prices.
        :param uom.uom uom: The uom to use to compute prices.
        :param dict kwargs: Locally unused data passed to overrides.
        :rtype: dict
        :return: A dict containing additional data about the specified product.
        """
        data = super()._get_additional_configurator_data(
            product_or_template, date, currency, pricelist, **kwargs
        )

        if (website := ir_http.get_request_website()) and product_or_template.is_product_variant:
            max_quantity = product_or_template._get_max_quantity(website, request.cart, **kwargs)
            if max_quantity is not None:
                if uom:
                    max_quantity = product_or_template.uom_id._compute_quantity(
                        max_quantity, to_unit=uom
                    )
                data["free_qty"] = max_quantity
        return data
