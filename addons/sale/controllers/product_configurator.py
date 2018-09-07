# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, fields
from odoo.http import request


class ProductConfiguratorController(http.Controller):
    @http.route(['/product_configurator/configure'], type='json', auth="user", methods=['POST'])
    def configure(self, product_id, pricelist_id, **kw):
        product_template = request.env['product.template'].browse(int(product_id))
        to_currency = product_template.currency_id
        pricelist = self._get_pricelist(pricelist_id)
        if pricelist:
            product_template = product_template.with_context(pricelist=pricelist.id, partner=request.env.user.partner_id)
            to_currency = pricelist.currency_id

        return request.env['ir.ui.view'].render_template("sale.product_configurator_configure", {
            'product': product_template,
            'to_currency': to_currency,
            'pricelist': pricelist,
            'get_attribute_value_ids': self._get_attribute_value_ids
        })

    @http.route(['/product_configurator/show_optional_products'], type='json', auth="user", methods=['POST'])
    def show_optional_products(self, product_id, pricelist_id, **kw):
        return self._show_optional_products(product_id, self._get_pricelist(pricelist_id), False, **kw)

    @http.route(['/product_configurator/optional_product_items'], type='json', auth="user", methods=['POST'])
    def optional_product_items(self, product_id, pricelist_id, **kw):
        return self._optional_product_items(product_id, self._get_pricelist(pricelist_id), **kw)

    @http.route(['/product_configurator/get_unit_price'], type='json', auth="user", methods=['POST'])
    def get_unit_price(self, product_ids, add_qty, pricelist_id, **kw):
        return self._get_unit_price(product_ids, add_qty, self._get_pricelist(pricelist_id))

    def _optional_product_items(self, product_id, pricelist, **kw):
        product = request.env['product.product'].with_context(self._get_product_context(pricelist, **kw)).browse(int(product_id))
        to_currency = product.currency_id
        if pricelist:
            to_currency = pricelist.currency_id

        return request.env['ir.ui.view'].render_template("sale.optional_product_items", {
            'product': product,
            'reference_product': product,
            'pricelist': pricelist,
            'to_currency': to_currency,
            'get_attribute_value_ids': self._get_attribute_value_ids,
            'main_product_attr_ids': self._get_main_product_attr_ids(product, pricelist=pricelist),
        })

    def _show_optional_products(self, product_id, pricelist, handle_stock, **kw):
        # quantity = kw['kwargs']['context']['quantity']

        product = request.env['product.product'].browse(int(product_id))
        from_currency = request.env.user.company_id.currency_id
        to_currency = pricelist.currency_id if pricelist else product.currency_id
        company = request.env['res.company'].browse(request.env.context.get('company_id')) or request.env['res.users']._get_company()
        date = request.env.context.get('date') or fields.Date.today()
        compute_currency = lambda price: from_currency._convert(price, to_currency, company, date)

        product = product.with_context(self._get_product_context(pricelist, **kw))

        has_optional_products = False
        for optional_product in product.optional_product_ids:
            if optional_product.get_filtered_variants(product):
                has_optional_products = True
                break

        if not has_optional_products:
            return False
        else:
            return request.env['ir.ui.view'].render_template("sale.optional_products_modal", {
                'product': product,
                'reference_product': product,
                'pricelist': pricelist,
                'compute_currency': compute_currency,
                'to_currency': to_currency,
                'handle_stock': handle_stock,
                'get_attribute_value_ids': self._get_attribute_value_ids,
                'main_product_attr_ids': self._get_main_product_attr_ids(product, pricelist=pricelist),
            })

    def _get_attribute_value_ids(self, product, reference_product=None, pricelist=None):
        """ list of selectable attributes of a product

        Args:
            - product (product.template): The base product template that will be split into variants
            - reference_product (product.product): The reference product from which 'product' is an optional or accessory product
            - pricelist (product.pricelist): A pricelist that will be used to compute the product price

        :return: list of product variant description
           (variant id, [visible attribute ids], variant price, variant sale price)
        """
        # product attributes with at least two choices
        quantity = product._context.get('quantity') or 1
        product = product.with_context(quantity=quantity, partner=request.env.user.partner_id)
        to_currency = None
        if pricelist:
            product = product.with_context(pricelist=pricelist.id)
            to_currency = pricelist.currency_id

        visible_attrs_ids = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id').ids
        attribute_value_ids = []
        for variant in product.get_filtered_variants(reference_product):
            public_price = variant.lst_price
            if to_currency and to_currency != product.currency_id:
                public_price = variant.currency_id._convert(
                    public_price, to_currency,
                    request.env.user.company_id, fields.Date.today()
                )

            visible_attribute_ids = [v.id for v in variant.product_attribute_value_ids if v.attribute_id.id in visible_attrs_ids]
            attribute_value_ids.append([variant.id, visible_attribute_ids, variant.price if variant.price else variant.lst_price, public_price, variant.display_name, len(variant.optional_product_ids) > 0])

        return attribute_value_ids

    def _get_main_product_attr_ids(self, product, pricelist=None):
        main_product_attr_ids = self._get_attribute_value_ids(product.product_tmpl_id, pricelist=pricelist)
        for variant in main_product_attr_ids:
            if variant[0] == product.id:
                # We indeed need a list of lists (even with only 1 element)
                main_product_attr_ids = [variant]
                break

        return main_product_attr_ids

    def _get_product_context(self, pricelist=None, **kw):
        product_context = dict(request.context)
        if pricelist:
            if not product_context.get('pricelist'):
                product_context['pricelist'] = pricelist.id
            product_context.update(kw.get('kwargs', {}).get('context', {}))

        return product_context

    def _get_unit_price(self, product_ids, add_qty, pricelist, **kw):
        products = request.env['product.product'].with_context({'quantity': add_qty, 'pricelist': pricelist.id if pricelist else None}).browse(product_ids)
        return {product.id: product.price if product.price else product.lst_price for product in products}

    def _get_pricelist(self, pricelist_id):
        return request.env['product.pricelist'].browse(int(pricelist_id)) if pricelist_id and pricelist_id != '0' else None
