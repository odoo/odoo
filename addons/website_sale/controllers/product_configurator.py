# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.tools import float_is_zero

from odoo.addons.sale.controllers.product_configurator import SaleProductConfiguratorController
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleProductConfiguratorController(SaleProductConfiguratorController, WebsiteSale):

    @route(
        route='/website_sale/should_show_product_configurator',
        type='json',
        auth='public',
        website=True,
    )
    def website_sale_should_show_product_configurator(
        self, product_template_id, ptav_ids, is_product_configured
    ):
        """ Return whether the product configurator dialog should be shown.

        :param int product_template_id: The product being checked, as a `product.template` id.
        :param list(int) ptav_ids: The combination of the product, as a list of
            `product.template.attribute.value` ids.
        :param bool is_product_configured: Whether the product is already configured.
        :rtype: bool
        :return: Whether the product configurator dialog should be shown.
        """
        product_template = request.env['product.template'].browse(product_template_id)
        combination = request.env['product.template.attribute.value'].browse(ptav_ids)
        single_product_variant = product_template.get_single_product_variant()
        # We can't use `single_product_variant.get('has_optional_products')` as it doesn't take
        # `combination` into account.
        has_optional_products = bool(product_template.optional_product_ids.filtered(
            lambda op: self._should_show_product(op, combination)
        ))
        force_dialog = request.website.add_to_cart_action == 'force_dialog'
        return (
            force_dialog
            or has_optional_products
            or not (single_product_variant.get('product_id') or is_product_configured)
        )

    def _get_product_template(self, product_template_id):
        if request.is_frontend:
            combo_item = request.env['product.combo.item'].sudo().search([
                ('product_id.product_tmpl_id.id', '=', product_template_id),
            ])
            if combo_item and request.env['product.template'].sudo().search_count([
                ('combo_ids', 'in', combo_item.mapped('combo_id.id')),
                ('website_published', '=', True),
            ]):
                return request.env['product.template'].sudo().browse(product_template_id)
        return super()._get_product_template(product_template_id)

    @route(
        route='/website_sale/product_configurator/get_values',
        type='json',
        auth='public',
        website=True,
    )
    def website_sale_product_configurator_get_values(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_get_values(*args, **kwargs)

    @route(
        route='/website_sale/product_configurator/create_product',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def website_sale_product_configurator_create_product(self, *args, **kwargs):
        return super().sale_product_configurator_create_product(*args, **kwargs)

    @route(
        route='/website_sale/product_configurator/update_combination',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def website_sale_product_configurator_update_combination(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_update_combination(*args, **kwargs)

    @route(
        route='/website_sale/product_configurator/get_optional_products',
        type='json',
        auth='public',
        website=True,
    )
    def website_sale_product_configurator_get_optional_products(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_get_optional_products(*args, **kwargs)

    @route(
        route='/website_sale/product_configurator/update_cart',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def website_sale_product_configurator_update_cart(
        self, main_product, optional_products, **kwargs
    ):
        """ Add the provided main and optional products to the cart.

        Main and optional products have the following shape:
        ```
        {
            'product_id': int,
            'product_template_id': int,
            'parent_product_template_id': int,
            'quantity': float,
            'product_custom_attribute_values': list(dict),
            'no_variant_attribute_value_ids': list(int),
        }
        ```

        Note: if product A is a parent of product B, then product A must come before product B in
        the optional_products list. Otherwise, the corresponding order lines won't be linked.

        :param dict main_product: The main product to add.
        :param list(dict) optional_products: The optional products to add.
        :param dict kwargs: Locally unused data passed to `_cart_update`.
        :rtype: dict
        :return: A dict containing information about the cart update.
        """
        order_sudo = request.website.sale_get_order(force_create=True)
        if order_sudo.state != 'draft':
            request.session['sale_order_id'] = None
            order_sudo = request.website.sale_get_order(force_create=True)

        # The main product could theoretically have a parent, but we ignore it to avoid
        # circularities in the linked line ids.
        values = order_sudo._cart_update(
            product_id=main_product['product_id'],
            add_qty=main_product['quantity'],
            product_custom_attribute_values=main_product['product_custom_attribute_values'],
            no_variant_attribute_value_ids=[
                int(value_id) for value_id in main_product['no_variant_attribute_value_ids']
            ],
            **kwargs,
        )
        line_ids = {main_product['product_template_id']: values['line_id']}

        if optional_products and values['line_id']:
            for option in optional_products:
                option_values = order_sudo._cart_update(
                    product_id=option['product_id'],
                    add_qty=option['quantity'],
                    product_custom_attribute_values=option['product_custom_attribute_values'],
                    no_variant_attribute_value_ids=[
                        int(value_id) for value_id in option['no_variant_attribute_value_ids']
                    ],
                    # Using `line_ids[...]` instead of `line_ids.get(...)` ensures that this throws
                    # if an optional product contains bad data.
                    linked_line_id=line_ids[option['parent_product_template_id']],
                    **kwargs,
                )
                line_ids[option['product_template_id']] = option_values['line_id']

        values['notification_info'] = self._get_cart_notification_information(
            order_sudo, line_ids.values()
        )
        values['cart_quantity'] = order_sudo.cart_quantity
        request.session['website_sale_cart_quantity'] = order_sudo.cart_quantity

        return values

    def _get_basic_product_information(
        self, product_or_template, pricelist, combination, currency=None, date=None, **kwargs
    ):
        """ Override of `sale` to append website data and apply taxes.

        :param product.product|product.template product_or_template: The product for which to seek
            information.
        :param product.pricelist pricelist: The pricelist to use.
        :param product.template.attribute.value combination: The combination of the product.
        :param res.currency|None currency: The currency of the transaction.
        :param datetime|None date: The date of the `sale.order`, to compute the price at the right
            rate.
        :param dict kwargs: Locally unused data passed to `super`.
        :rtype: dict
        :return: A dict with the following structure:
            {
                ...  # fields from `super`.
                'price': float,
                'can_be_sold': bool,
                'category_name': str,
                'currency_name': str,
                'strikethrough_price': float,  # if there's a strikethrough_price to display.
            }
        """
        basic_product_information = super()._get_basic_product_information(
            product_or_template.with_context(display_default_code=not request.is_frontend),
            pricelist,
            combination,
            currency=currency,
            date=date,
            **kwargs,
        )

        if request.is_frontend:
            has_zero_price = float_is_zero(
                basic_product_information['price'], precision_rounding=currency.rounding
            )
            basic_product_information['can_be_sold'] = not (
                request.website.prevent_zero_price_sale and has_zero_price
            )
            # Don't compute the strikethrough price if there's a custom price (i.e. if `price_info`
            # is populated).
            strikethrough_price = self._get_strikethrough_price(
                product_or_template.with_context(
                    **product_or_template._get_product_price_context(combination)
                ),
                currency,
                date,
                basic_product_information['price'],
                basic_product_information['pricelist_rule_id'],
            ) if 'price_info' not in basic_product_information else None
            if strikethrough_price:
                basic_product_information['strikethrough_price'] = strikethrough_price
        return basic_product_information

    def _get_ptav_price_extra(self, ptav, currency, date, product_or_template):
        """ Override of `sale` to apply taxes.

        :param product.template.attribute.value ptav: The product template attribute value for which
            to compute the extra price.
        :param res.currency currency: The currency to compute the extra price in.
        :param datetime date: The date to compute the extra price at.
        :param product.product|product.template product_or_template: The product on which the
            product template attribute value applies.
        :rtype: float
        :return: The extra price for the product template attribute value.
        """
        price_extra = super()._get_ptav_price_extra(ptav, currency, date, product_or_template)
        if request.is_frontend:
            return self._apply_taxes_to_price(price_extra, product_or_template, currency)
        return price_extra

    def _get_strikethrough_price(self, product_or_template, currency, date, price, pricelist_rule_id=None):
        """ Return the strikethrough price of the product, if there is one.

        :param product.product|product.template product_or_template: The product for which to
            compute the strikethrough price.
        :param res.currency currency: The currency to compute the strikethrough price in.
        :param datetime date: The date to compute the strikethrough price at.
        :param float price: The actual price of the product.
        :rtype: float|None
        :return: The strikethrough price of the product, if there is one.
        """
        pricelist_rule = request.env['product.pricelist.item'].browse(pricelist_rule_id)

        # First, try to use the base price as the strikethrough price.
        # Apply taxes before comparing it to the actual price.
        if pricelist_rule._show_discount_on_shop():
            pricelist_base_price = self._apply_taxes_to_price(
                pricelist_rule._compute_price_before_discount(
                    product=product_or_template,
                    quantity=1.0,
                    uom=product_or_template.uom_id,
                    date=date,
                    currency=currency,
                ),
                product_or_template,
                currency,
            )
            # Only show the base price if it's greater than the actual price.
            if currency.compare_amounts(pricelist_base_price, price) == 1:
                return pricelist_base_price

        # Second, try to use `compare_list_price` as the strikethrough price.
        # Don't apply taxes since this price should always be displayed as is.
        if (
            request.env.user.has_group('website_sale.group_product_price_comparison')
            and product_or_template.compare_list_price
        ):
            compare_list_price = product_or_template.currency_id._convert(
                from_amount=product_or_template.compare_list_price,
                to_currency=currency,
                company=request.env.company,
                date=date,
                round=False,
            )
            # Only show `compare_list_price` if it's greater than the actual price.
            if currency.compare_amounts(compare_list_price, price) == 1:
                return compare_list_price
        return None

    def _should_show_product(self, product_template, parent_combination):
        """ Override of `sale` to only show products that can be added to the cart.

        :param product.template product_template: The product being checked.
        :param product.template.attribute.value parent_combination: The combination of the parent
            product.
        :rtype: bool
        :return: Whether the product should be shown in the configurator.
        """
        should_show_product = super()._should_show_product(product_template, parent_combination)
        if request.is_frontend:
            return (
                should_show_product
                and product_template._is_add_to_cart_possible(parent_combination)
                and product_template.filtered_domain(request.website.website_domain())
            )
        return should_show_product

    @staticmethod
    def _apply_taxes_to_price(price, product_or_template, currency):
        product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(
            request.env.company
        )
        if product_taxes:
            fiscal_position = request.website.fiscal_position_id.sudo()
            taxes = fiscal_position.map_tax(product_taxes)
            return request.env['product.template']._apply_taxes_to_price(
                price, currency, product_taxes, taxes, product_or_template, website=request.website
            )
        return price
