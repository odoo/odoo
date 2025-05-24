# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.tools.image import image_data_uri

from odoo.addons.sale.controllers.combo_configurator import SaleComboConfiguratorController
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleComboConfiguratorController(SaleComboConfiguratorController, WebsiteSale):

    @route(
        route='/website_sale/combo_configurator/get_data',
        type='json',
        auth='public',
        website=True,
    )
    def website_sale_combo_configurator_get_data(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        request.update_context(display_default_code=False)  # Hide internal product reference
        res = super().sale_combo_configurator_get_data(*args, **kwargs)
        res.update({
            'show_quantity': (
                bool(request.website.is_view_active('website_sale.product_quantity'))
            ),
        })
        return res

    @route(
        route='/website_sale/combo_configurator/get_price',
        type='json',
        auth='public',
        website=True,
    )
    def website_sale_combo_configurator_get_price(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_combo_configurator_get_price(*args, **kwargs)

    @route(
        route='/website_sale/combo_configurator/update_cart',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def website_sale_combo_configurator_update_cart(
        self, combo_product_id, quantity, selected_combo_items, **kwargs
    ):
        """ Add the provided combo product and selected combo items to the cart.

        :param int combo_product_id: The combo product to add, as a `product.product` id.
        :param int quantity: The quantity to add.
        :param list(dict) selected_combo_items: The selected combo items to add.
        :param dict kwargs: Locally unused data passed to `_cart_update`.
        :rtype: dict
        :return: A dict containing information about the cart update.
        """
        if not selected_combo_items:
            raise UserError(_("A combo product can't be empty. Please select at least one option."))

        order_sudo = request.website.sale_get_order(force_create=True)
        if order_sudo.state != 'draft':
            request.session['sale_order_id'] = None
            order_sudo = request.website.sale_get_order(force_create=True)

        combo_quantity, warning = order_sudo._verify_updated_quantity(
            request.env['sale.order.line'], combo_product_id, quantity, **kwargs
        )
        # A combo product and its items should have the same quantity (by design). So, if the
        # requested quantity isn't available for one or more combo items, we should lower the
        # quantity of the combo product and its items to the maximum available quantity of the
        # combo item with the least available quantity.
        for combo_item in selected_combo_items:
            combo_item_quantity, warning = order_sudo._verify_updated_quantity(
                request.env['sale.order.line'], combo_item['product_id'], quantity, **kwargs
            )
            combo_quantity = min(combo_quantity, combo_item_quantity)

        values = order_sudo._cart_update(
            product_id=combo_product_id,
            set_qty=combo_quantity,
            **kwargs,
        )
        line_ids = [values['line_id']]

        if selected_combo_items and values['line_id']:
            for combo_item in selected_combo_items:
                item_values = order_sudo._cart_update(
                    product_id=combo_item['product_id'],
                    set_qty=combo_quantity,
                    product_custom_attribute_values=combo_item['product_custom_attribute_values'],
                    no_variant_attribute_value_ids=[
                        int(value_id) for value_id in combo_item['no_variant_attribute_value_ids']
                    ],
                    linked_line_id=values['line_id'],
                    combo_item_id=combo_item['combo_item_id'],
                    **kwargs,
                )
                line_ids.append(item_values['line_id'])

        # The price of a combo product (and thus whether it can be added to the cart) can only be
        # computed after creating all of its combo item lines.
        combo_product_line = request.env['sale.order.line'].browse(values['line_id'])
        if (
            combo_product_line
            and sum(combo_product_line._get_lines_with_price().mapped('price_unit')) == 0
            and combo_product_line.order_id.website_id.prevent_zero_price_sale
        ):
            raise UserError(_(
                "The given product does not have a price therefore it cannot be added to cart.",
            ))
        values['notification_info'] = self._get_cart_notification_information(order_sudo, line_ids)
        values['cart_quantity'] = order_sudo.cart_quantity
        request.session['website_sale_cart_quantity'] = order_sudo.cart_quantity

        return values

    def _get_combo_item_data(
        self, combo, combo_item, selected_combo_item, date, currency, pricelist, **kwargs
    ):
        data = super()._get_combo_item_data(
            combo, combo_item, selected_combo_item, date, currency, pricelist, **kwargs
        )
        # To sell a product type 'combo', one doesn't need to publish all combo choices. This causes
        # an issue when public users access the image of each choice via the /web/image route. To
        # bypass this access check, we send the raw image URL if the product is inaccessible to the
        # current user.
        if (
            not combo_item.product_id.sudo(False).has_access('read')
            and (combo_item_image := combo_item.product_id.image_256)
        ):
            data['product']['image_src'] = image_data_uri(combo_item_image)
        return data
