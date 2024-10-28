# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

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
        return super().sale_combo_configurator_get_data(*args, **kwargs)

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

        :param int combo_product_id: The combo product to add, as a `product.template` id.
        :param int quantity: The quantity to add.
        :param list(dict) selected_combo_items: The selected combo items to add.
        :param dict kwargs: Locally unused data passed to `_cart_update`.
        :rtype: dict
        :return: A dict containing information about the cart update.
        """
        order_sudo = request.website.sale_get_order(force_create=True)
        if order_sudo.state != 'draft':
            request.session['sale_order_id'] = None
            order_sudo = request.website.sale_get_order(force_create=True)

        values = order_sudo._cart_update(
            product_id=combo_product_id,
            line_id=False,  # Always create a new line for combo products.
            set_qty=quantity,
            **kwargs,
        )
        line_ids = [values['line_id']]

        if selected_combo_items and values['line_id']:
            for combo_item in selected_combo_items:
                item_values = order_sudo._cart_update(
                    product_id=combo_item['product_id'],
                    line_id=False,
                    set_qty=quantity,
                    product_custom_attribute_values=combo_item['product_custom_attribute_values'],
                    no_variant_attribute_value_ids=[
                        int(value_id) for value_id in combo_item['no_variant_attribute_value_ids']
                    ],
                    linked_line_id=values['line_id'],
                    combo_item_id=combo_item['combo_item_id'],
                    **kwargs,
                )
                line_ids.append(item_values['line_id'])

        values['notification_info'] = self._get_cart_notification_information(order_sudo, line_ids)
        values['cart_quantity'] = order_sudo.cart_quantity
        request.session['website_sale_cart_quantity'] = order_sudo.cart_quantity

        return values
