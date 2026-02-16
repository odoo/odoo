# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.sale.controllers.product_configurator import SaleProductConfiguratorController
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleProductConfiguratorController(SaleProductConfiguratorController, WebsiteSale):

    @route(
        route='/website_sale/should_show_product_configurator',
        type='jsonrpc',
        auth='public',
        website=True,
        readonly=True,
    )
    def website_sale_should_show_product_configurator(
        self, product_template_id, ptav_ids, is_product_configured, quantity
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
        result = product_template.get_single_product_variant(quantity)
        has_optional_products = bool(
            product_template.optional_product_ids.filtered(self._should_show_product)
        )
        if (
            has_optional_products
            or not (result.get('product_id') or is_product_configured)
        ):
            return result
        else:
            return False

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
        type='jsonrpc',
        auth='public',
        website=True,
        readonly=True,
    )
    def website_sale_product_configurator_get_values(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        product_template = request.env['product.template'].browse(
        kwargs.get('product_template_id')
        )

        return product_template.sale_product_configurator_get_values(
            **kwargs
        )

    @route(
        route='/website_sale/product_configurator/create_product',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def website_sale_product_configurator_create_product(self, *args, **kwargs):
        return super().sale_product_configurator_create_product(*args, **kwargs)

    @route(
        route='/website_sale/product_configurator/update_combination',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def website_sale_product_configurator_update_combination(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_update_combination(*args, **kwargs)

    @route(
        route='/website_sale/product_configurator/get_optional_products',
        type='jsonrpc',
        auth='public',
        website=True,
        readonly=True,
    )
    def website_sale_product_configurator_get_optional_products(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_product_configurator_get_optional_products(*args, **kwargs)

    def _should_show_product(self, product_template):
        """ Override of `sale` to only show products that can be added to the cart.

        :param product.template product_template: The product being checked.
        :rtype: bool
        :return: Whether the product should be shown in the configurator.
        """
        should_show_product = super()._should_show_product(product_template)
        if request.is_frontend:
            return (
                should_show_product
                and product_template._is_add_to_cart_possible()
                and product_template.filtered_domain(request.website.website_domain())
            )
        return should_show_product

    @staticmethod
    def _apply_taxes_to_price(price, product_or_template, currency):
        product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(
            request.env.company
        )
        if product_taxes:
            taxes = request.fiscal_position.map_tax(product_taxes)
            return request.env['product.template']._apply_taxes_to_price(
                price, currency, product_taxes, taxes, product_or_template, website=request.website
            )
        return price
