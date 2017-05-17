# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_round


class report_product_pricelist(models.AbstractModel):
    _name = 'report.product.report_pricelist'

    @api.model
    def get_report_values(self, docids, data=None):
        data = data if data is not None else {}
        pricelist = self.env['product.pricelist'].browse(data.get('form', {}).get('price_list', False))
        active_model = self.env.context.get('active_model')
        products = self.env[active_model].browse(data.get('ids'))
        quantities = self._get_quantity(data)
        return {
            'doc_ids': data.get('ids', data.get('active_ids')),
            'doc_model': 'hr.contribution.register',
            'docs': products,
            'data': dict(
                data,
                pricelist=pricelist,
                quantities=quantities,
                categories_data=self._get_categories(pricelist, products, quantities)
            ),
        }

    def _get_quantity(self, data):
        return sorted([data['form'][key] for key in data['form'] if key.startswith('qty') and data['form'][key]])

    def _get_categories(self, pricelist, products, quantities):
        categ_data = []
        categories = self.env['product.category']
        for product in products:
            categories |= product.categ_id

        for category in categories:
            categ_products = products.filtered(lambda product: product.categ_id == category)
            prices = {}
            if self.env.context.get('active_model') == 'product.template':
                categ_products = (map((lambda product: product.product_variant_ids), categ_products))
            for product_variants in categ_products:
                for product in product_variants:
                    prices[product.id] = dict.fromkeys(quantities, 0.0)
                    for quantity in quantities:
                        prices[product.id][quantity] = self._get_price(pricelist, product, quantity)
            categ_data.append({
                'category': category,
                'products': categ_products,
                'prices': prices,
            })
        return categ_data

    def _get_price(self, pricelist, product, qty):
        sale_price_digits = self.env['decimal.precision'].precision_get('Product Price')
        price = pricelist.get_product_price(product, qty, False)
        if not price:
            price = product.list_price
        return float_round(price, precision_digits=sale_price_digits)
