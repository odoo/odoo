# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class WebsiteSaleProductConfiguratorController(Controller):

    @route(
        '/sale_product_configurator/show_advanced_configurator',
        type='json', auth='public', methods=['POST'], website=True,
    )
    def show_advanced_configurator(
        self, product_id, variant_values, add_qty=1, force_dialog=False, **kw,
    ):
        product = request.env['product.product'].browse(int(product_id))
        product_template = product.product_tmpl_id
        combination = request.env['product.template.attribute.value'].browse(variant_values)
        has_optional_products = product.optional_product_ids.filtered(
            lambda p: p._is_add_to_cart_possible(combination)
                      and (not request.website.prevent_zero_price_sale or p._get_contextual_price())
        )

        already_configured = bool(combination)
        if not force_dialog and not has_optional_products and (
            not product.has_configurable_attributes or already_configured
        ):
            # The modal is not shown if there are no optional products and
            # the main product either has no variants or is already configured
            return False

        add_qty = float(add_qty)
        combination_info = product_template._get_combination_info(
            combination=combination,
            product_id=product.id,
            add_qty=add_qty,
        )

        return request.env['ir.ui.view']._render_template(
            'website_sale_product_configurator.optional_products_modal',
            {
                'product': product,
                'product_template': product_template,
                'combination': combination,
                'combination_info': combination_info,
                'add_qty': add_qty,
                'parent_name': product.name,
                'variant_values': variant_values,
                'already_configured': already_configured,
                'mode': kw.get('mode', 'add'),
                'product_custom_attribute_values': kw.get('product_custom_attribute_values', None),
                'no_attribute': kw.get('no_attribute', False),
                'custom_attribute': kw.get('custom_attribute', False),
            }
        )

    @route(
        '/sale_product_configurator/optional_product_items',
        type='json', auth='public', methods=['POST'], website=True,
    )
    def optional_product_items(self, product_id, add_qty=1, **kw):
        product = request.env['product.product'].browse(int(product_id))

        return request.env['ir.ui.view']._render_template(
            'website_sale_product_configurator.optional_product_items',
            {
                'product': product,
                'parent_name': product.name,
                'parent_combination': product.product_template_attribute_value_ids,
                'add_qty': float(add_qty) or 1.0,
            }
        )
