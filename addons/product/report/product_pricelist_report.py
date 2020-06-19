# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class report_product_pricelist(models.AbstractModel):
    _name = 'report.product.report_pricelist'
    _description = 'Pricelist Report'

    def _get_report_values(self, docids, data):
        product_ids = [int(i) for i in data['active_ids'].split(',')]
        pricelist_id = data['pricelist_id'] and int(data['pricelist_id']) or None
        quantities = [int(i) for i in data['quantities'].split(',')] or [1]
        return self._get_report_data(data['active_model'], product_ids, pricelist_id, quantities, 'pdf')

    @api.model
    def get_html(self):
        render_values = self._get_report_data(
            self.env.context.get('active_model'),
            self.env.context.get('active_ids'),
            self.env.context.get('pricelist_id'),
            self.env.context.get('quantities') or [1]
        )
        return self.env.ref('product.report_pricelist_page')._render(render_values)

    def _get_report_data(self, active_model, active_ids, pricelist_id, quantities, report_type='html'):
        products = []
        is_product_tmpl = active_model == 'product.template'

        ProductClass = self.env['product.template'] if is_product_tmpl else self.env['product.product']
        ProductPricelist = self.env['product.pricelist']
        pricelist = ProductPricelist.browse(pricelist_id)
        if not pricelist:
            pricelist = ProductPricelist.search([], limit=1)

        if is_product_tmpl:
            records = ProductClass.browse(active_ids) if active_ids else ProductClass.search([('sale_ok', '=', True)])
            for product in records:
                product_data = self._get_product_data(is_product_tmpl, product, pricelist, quantities)
                variants = []
                if len(product.product_variant_ids) > 1:
                    for variant in product.product_variant_ids:
                        variants.append(self._get_product_data(False, variant, pricelist, quantities))
                product_data['variants'] = variants
                products.append(product_data)
        else:
            records = ProductClass.browse(active_ids) if active_ids else ProductClass.search([('sale_ok', '=', True)])
            for product in records:
                products.append(self._get_product_data(is_product_tmpl, product, pricelist, quantities))

        return {
            'pricelist': pricelist,
            'products': products,
            'quantities': quantities,
            'is_product_tmpl': is_product_tmpl,
            'is_html_type': report_type == 'html',
        }

    def _get_product_data(self, is_product_tmpl, product, pricelist, quantities):
        data = {
            'id': product.id,
            'name': is_product_tmpl and product.name or product.display_name,
            'price': dict.fromkeys(quantities, 0.0),
        }
        for qty in quantities:
            data['price'][qty] = pricelist.get_product_price(product, qty, False)
        return data
