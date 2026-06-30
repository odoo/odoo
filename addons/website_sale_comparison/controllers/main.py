# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class WebsiteSaleProductComparison(Controller):

    @route('/shop/compare', type='http', auth='public', website=True, sitemap=False)
    def product_compare(self, **post):
        product_ids = [int(i) for i in post.get('products', '').split(',') if i.isdigit()]
        if not product_ids:
            return request.redirect('/shop')

        # use search to check read access on each record/ids
        products = request.env['product.product'].search([('id', 'in', product_ids)])
        return request.render(
            'website_sale_comparison.product_compare',
            {
                'products': products.with_context(display_default_code=False),
            }
        )

    @route('/shop/compare/get_product_data', type='jsonrpc', auth='public', website=True)
    def get_product_data(self, product_ids):
        products = request.env['product.product'].search([('id', 'in', product_ids)])
        product_data = []

        for product in products:
            combination_info = product._get_combination_info_variant()
            product_data_item = {
                'id': product.id,
                'display_name': combination_info['display_name'],
                'website_url': product.website_url,
                'image_url': product._get_image_1024_url(),
                'price': combination_info['price'],
                'prevent_zero_price_sale': combination_info['prevent_zero_price_sale'],
                'currency_id': combination_info['currency'].id,
            }
            if combination_info['has_discounted_price']:
                product_data_item['strikethrough_price'] = combination_info['list_price']
            elif (
                combination_info.get('compare_list_price')
                and combination_info['compare_list_price'] > combination_info['price']
            ):
                product_data_item['strikethrough_price'] = combination_info['compare_list_price']
            product_data.append(product_data_item)

        return product_data
