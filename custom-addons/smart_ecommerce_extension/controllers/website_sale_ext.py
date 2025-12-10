# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExtension(WebsiteSale):
    """Extend website sale controller with additional filters and features"""

    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        """Extend search domain with brand and availability filters"""
        domain = super()._get_search_domain(
            search, category, attrib_values, search_in_description
        )
        
        # Brand filter
        brand = request.params.get('brand')
        if brand:
            domain.append(('brand', '=', brand))
        
        # Availability filter
        availability = request.params.get('availability')
        if availability and availability in ('in_stock', 'low_stock', 'out_of_stock'):
            domain.append(('availability_status', '=', availability))
        
        # Price range filter
        price_min = request.params.get('price_min')
        price_max = request.params.get('price_max')
        if price_min:
            try:
                domain.append(('list_price', '>=', float(price_min)))
            except ValueError:
                pass
        if price_max:
            try:
                domain.append(('list_price', '<=', float(price_max)))
            except ValueError:
                pass
        
        return domain

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        """Override shop to add filter data to template"""
        response = super().shop(
            page=page,
            category=category,
            search=search,
            min_price=min_price,
            max_price=max_price,
            ppg=ppg,
            **post
        )
        
        # Add brand list for filtering
        Product = request.env['product.template'].sudo()
        brands = Product.get_brands()
        
        # Get price range for slider
        request.env.cr.execute("""
            SELECT MIN(list_price), MAX(list_price)
            FROM product_template
            WHERE is_published = true AND sale_ok = true
        """)
        price_range = request.env.cr.fetchone()
        
        # Add to template values
        response.qcontext.update({
            'brands': brands,
            'selected_brand': post.get('brand'),
            'selected_availability': post.get('availability'),
            'price_range_min': price_range[0] or 0,
            'price_range_max': price_range[1] or 1000,
            'selected_price_min': post.get('price_min', ''),
            'selected_price_max': post.get('price_max', ''),
        })
        
        return response

    @http.route('/shop/delivery_estimate', type='json', auth='public', website=True)
    def get_delivery_estimate(self, product_id=None, city=None, **kwargs):
        """AJAX endpoint to get delivery estimate for a product"""
        if not product_id:
            return {'error': 'Product ID required'}
        
        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'error': 'Product not found'}
        
        estimate = product.get_estimated_delivery_date(city=city)
        
        # Get delivery zone info
        zone_info = None
        if city:
            zone = request.env['delivery.zone'].sudo().find_zone_for_city(city)
            if zone:
                zone_info = {
                    'name': zone.name,
                    'price': zone.base_price,
                    'currency': zone.currency_id.symbol,
                }
        
        return {
            'estimate': estimate,
            'zone': zone_info,
        }

