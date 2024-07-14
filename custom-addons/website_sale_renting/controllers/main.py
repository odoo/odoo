# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields

from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleRenting(WebsiteSale):

    @route('/shop/cart/update_renting', type='json', auth="public", methods=['POST'], website=True)
    def cart_update_renting(self, start_date=None, end_date=None):
        """Route to check the cart availability when changing the dates on the cart.
        """
        if not start_date or not end_date:
            return
        order_sudo = request.website.sale_get_order()
        if not order_sudo:
            return
        start_date = fields.Datetime.to_datetime(start_date)
        end_date = fields.Datetime.to_datetime(end_date)
        order_sudo._cart_update_renting_period(start_date, end_date)

        values = {}
        values['cart_ready'] = order_sudo._is_cart_ready()
        values['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template(
            'website_sale.cart_lines', {
                'website_sale_order': order_sudo,
                'date': fields.Date.today(),
                'suggested_products': order_sudo._cart_accessories(),
            }
        )
        values['website_sale.total'] = request.env['ir.ui.view']._render_template(
            'website_sale.total', {
                'website_sale_order': order_sudo,
            }
        )
        return {
            'start_date': order_sudo.rental_start_date,
            'end_date': order_sudo.rental_return_date,
            'values': values,
        }

    def _get_search_options(self, **post):
        options = super()._get_search_options(**post)
        options.update({
            'from_date': post.get('start_date'),
            'to_date': post.get('end_date'),
            'rent_only': post.get('rent_only') in ('True', 'true', '1'),
        })
        return options

    def _shop_get_query_url_kwargs(self, category, search, min_price, max_price, **post):
        result = super()._shop_get_query_url_kwargs(category, search, min_price, max_price, **post)
        result.update(
            start_date=post.get('start_date'),
            end_date=post.get('end_date'),
        )
        return result

    def _product_get_query_url_kwargs(self, category, search, **kwargs):
        result = super()._product_get_query_url_kwargs(category, search, **kwargs)
        result.update(
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
        )
        return result

    def _prepare_product_values(self, product, category, search, start_date=None, end_date=None, **kwargs):
        result = super()._prepare_product_values(product, category, search, **kwargs)
        result.update(
            start_date=fields.Datetime.to_datetime(start_date),
            end_date=fields.Datetime.to_datetime(end_date),
        )
        return result
