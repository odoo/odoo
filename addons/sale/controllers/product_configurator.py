# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, fields
from odoo.http import request


class ProductConfiguratorController(http.Controller):
    @http.route(['/product_configurator/configure'], type='json', auth="user", methods=['POST'])
    def configure(self, product_id, pricelist_id, **kw):
        add_qty = int(kw.get('add_qty', 1))
        product_template = request.env['product.template'].browse(int(product_id))
        to_currency = product_template.currency_id
        pricelist = self._get_pricelist(pricelist_id)

        if pricelist:
            product_template = product_template.with_context(pricelist=pricelist.id, partner=request.env.user.partner_id)
            to_currency = pricelist.currency_id

        return request.env['ir.ui.view'].render_template("sale.product_configurator_configure", {
            'product': product_template,
            # to_currency deprecated, get it from the pricelist or product directly
            'to_currency': to_currency,
            'pricelist': pricelist,
            'add_qty': add_qty,
            # get_attribute_exclusions deprecated, use product method
            'get_attribute_exclusions': self._get_attribute_exclusions
        })

    @http.route(['/product_configurator/show_optional_products'], type='json', auth="user", methods=['POST'])
    def show_optional_products(self, product_id, variant_values, pricelist_id, **kw):
        pricelist = self._get_pricelist(pricelist_id)
        return self._show_optional_products(product_id, variant_values, pricelist, False, **kw)

    @http.route(['/product_configurator/optional_product_items'], type='json', auth="user", methods=['POST'])
    def optional_product_items(self, product_id, pricelist_id, **kw):
        pricelist = self._get_pricelist(pricelist_id)
        return self._optional_product_items(product_id, pricelist, **kw)

    @http.route(['/product_configurator/get_combination_info'], type='json', auth="user", methods=['POST'])
    def get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist_id, **kw):
        combination = request.env['product.template.attribute.value'].browse(combination)
        pricelist = self._get_pricelist(pricelist_id)
        return request.env['product.template'].browse(int(product_template_id))._get_combination_info(combination, int(product_id or 0), int(add_qty or 1), pricelist)

    @http.route(['/product_configurator/create_product_variant'], type='json', auth="user", methods=['POST'])
    def create_product_variant(self, product_template_id, product_template_attribute_value_ids, **kwargs):
        return request.env['product.template'].browse(int(product_template_id)).create_product_variant(product_template_attribute_value_ids)

    def _optional_product_items(self, product_id, pricelist, **kw):
        add_qty = int(kw.get('add_qty', 1))
        product = request.env['product.product'].with_context(self._get_product_context(pricelist, **kw)).browse(int(product_id))
        to_currency = product.currency_id

        if pricelist:
            to_currency = pricelist.currency_id

        parent_combination = product.product_template_attribute_value_ids
        if product.env.context.get('no_variant_attribute_values'):
            # Add "no_variant" attribute values' exclusions
            # They are kept in the context since they are not linked to this product variant
            parent_combination |= product.env.context.get('no_variant_attribute_values')

        return request.env['ir.ui.view'].render_template("sale.optional_product_items", {
            # product deprecated, it's not used in the view
            'product': product,
            # reference_product deprecated, use parent_combination instead
            'reference_product': product,
            'parent_combination': parent_combination,
            'pricelist': pricelist,
            # to_currency deprecated, get from pricelist or product
            'to_currency': to_currency,
            # get_attribute_exclusions deprecated, use product method
            'get_attribute_exclusions': self._get_attribute_exclusions,
            'add_qty': add_qty,
        })

    def _show_optional_products(self, product_id, variant_values, pricelist, handle_stock, **kw):
        product = request.env['product.product'].with_context(self._get_product_context(pricelist, **kw)).browse(int(product_id))
        combination = request.env['product.template.attribute.value'].browse(variant_values)
        has_optional_products = product.optional_product_ids.filtered(lambda p: p._is_add_to_cart_possible(combination))

        if not has_optional_products:
            return False

        add_qty = int(kw.get('add_qty', 1))
        to_currency = (pricelist or product).currency_id
        company = request.env['res.company'].browse(request.env.context.get('company_id')) or request.env['res.users']._get_company()
        date = request.env.context.get('date') or fields.Date.today()

        def compute_currency(price):
            return product.currency_id._convert(price, to_currency, company, date)

        no_variant_attribute_values = combination.filtered(
            lambda product_template_attribute_value: product_template_attribute_value.attribute_id.create_variant == 'no_variant'
        )
        if no_variant_attribute_values:
            product = product.with_context(no_variant_attribute_values=no_variant_attribute_values)

        return request.env['ir.ui.view'].render_template("sale.optional_products_modal", {
            'product': product,
            'combination': combination,
            'add_qty': add_qty,
            # reference_product deprecated, use combination instead
            'reference_product': product,
            'variant_values': variant_values,
            'pricelist': pricelist,
            # compute_currency deprecated, get from pricelist or product
            'compute_currency': compute_currency,
            # to_currency deprecated, get from pricelist or product
            'to_currency': to_currency,
            'handle_stock': handle_stock,
            # get_attribute_exclusions deprecated, use product method
            'get_attribute_exclusions': self._get_attribute_exclusions,
        })

    def _get_attribute_exclusions(self, product, reference_product=None):
        """deprecated, use product method"""
        parent_combination = request.env['product.template.attribute.value']
        if reference_product:
            parent_combination |= reference_product.product_template_attribute_value_ids
            if reference_product.env.context.get('no_variant_attribute_values'):
                # Add "no_variant" attribute values' exclusions
                # They are kept in the context since they are not linked to this product variant
                parent_combination |= reference_product.env.context.get('no_variant_attribute_values')
        return product._get_attribute_exclusions(parent_combination)

    def _get_product_context(self, pricelist=None, **kw):
        """deprecated, can be removed in master"""
        product_context = dict(request.context)
        if pricelist:
            if not product_context.get('pricelist'):
                product_context['pricelist'] = pricelist.id
            product_context.update(kw.get('kwargs', {}).get('context', {}))

        return product_context

    def _get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist, **kw):
        """deprecated, use product method"""
        combination = request.env['product.template.attribute.value'].browse(combination)
        return request.env['product.template'].browse(product_template_id)._get_combination_info(combination, product_id, add_qty, pricelist)

    def _get_pricelist(self, pricelist_id, pricelist_fallback=False):
        return request.env['product.pricelist'].browse(int(pricelist_id or 0))
