# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


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
        """Override shop to add filter data and categories to template"""
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
        
        # Get all published categories with product count
        Category = request.env['product.public.category'].sudo()
        categories = Category.search([('parent_id', '=', False)])  # Top-level categories
        
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
            'categories': categories,
            'selected_brand': post.get('brand'),
            'selected_availability': post.get('availability'),
            'price_range_min': price_range[0] or 0,
            'price_range_max': price_range[1] or 1000,
            'selected_price_min': post.get('price_min', ''),
            'selected_price_max': post.get('price_max', ''),
        })
        
        return response

    @http.route('/shop/payment/validate', type='http', auth='public', website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **post):
        """Override to ensure order is properly confirmed and visible in backend"""
        response = super().shop_payment_validate(sale_order_id=sale_order_id, **post)
        
        # Get the confirmed order
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(int(sale_order_id))
        else:
            order = request.website.sale_get_order()
        
        if order and order.exists():
            # Ensure the order is confirmed (not draft)
            if order.state == 'draft':
                try:
                    order.action_confirm()
                    _logger.info(f"Order {order.name} confirmed from website checkout")
                except Exception as e:
                    _logger.error(f"Failed to confirm order {order.name}: {str(e)}")
            
            # Log order details for tracking
            _logger.info(
                f"Website Order Submitted: {order.name}, "
                f"Customer: {order.partner_id.name}, "
                f"Amount: {order.amount_total} {order.currency_id.name}, "
                f"State: {order.state}"
            )
        
        return response

    @http.route('/shop/confirmation', type='http', auth='public', website=True, sitemap=False)
    def shop_payment_confirmation(self, **post):
        """Override confirmation page to show order details"""
        response = super().shop_payment_confirmation(**post)
        
        # Get the last confirmed order for this session
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            if order.exists():
                # Add extra order info to template
                response.qcontext.update({
                    'order': order,
                    'order_confirmed': order.state in ('sale', 'done'),
                    'estimated_delivery': order.estimated_delivery_date if hasattr(order, 'estimated_delivery_date') else None,
                    'delivery_zone': order.delivery_zone_id.name if hasattr(order, 'delivery_zone_id') and order.delivery_zone_id else None,
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

    @http.route('/shop/set_delivery_zone', type='json', auth='public', website=True)
    def set_delivery_zone(self, zone_id=None, **kwargs):
        """AJAX endpoint to set the delivery zone for the current cart"""
        if not zone_id:
            return {'success': False, 'error': 'Zone ID required'}
        
        order = request.website.sale_get_order()
        if not order:
            return {'success': False, 'error': 'No active cart found'}
        
        zone = request.env['delivery.zone'].sudo().browse(int(zone_id))
        if not zone.exists():
            return {'success': False, 'error': 'Delivery zone not found'}
        
        try:
            # Update the order's delivery zone
            order.sudo().write({
                'delivery_zone_id': zone.id,
            })
            
            # Compute delivery price
            delivery_price = zone.compute_delivery_price(
                order.total_shipping_weight or 1.0,
                order.amount_untaxed
            )
            
            # Format price for display
            currency = order.currency_id
            delivery_price_formatted = f"{currency.symbol}{delivery_price:.2f}"
            
            _logger.info(
                f"Delivery zone set for order {order.name}: "
                f"Zone={zone.name}, Price={delivery_price}"
            )
            
            return {
                'success': True,
                'zone_id': zone.id,
                'zone_name': zone.name,
                'delivery_price': delivery_price,
                'delivery_price_formatted': delivery_price_formatted,
                'estimated_days': zone.estimated_days,
            }
        except Exception as e:
            _logger.error(f"Failed to set delivery zone: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/shop/get_delivery_zones', type='json', auth='public', website=True)
    def get_delivery_zones(self, **kwargs):
        """AJAX endpoint to get available delivery zones"""
        zones = request.env['delivery.zone'].sudo().search([('active', '=', True)])
        
        order = request.website.sale_get_order()
        currency = order.currency_id if order else request.env.company.currency_id
        
        return {
            'zones': [{
                'id': zone.id,
                'name': zone.name,
                'base_price': zone.base_price,
                'base_price_formatted': f"{currency.symbol}{zone.base_price:.2f}",
                'estimated_days': zone.estimated_days,
                'free_threshold': zone.free_delivery_threshold,
                'cities': zone.cities or '',
            } for zone in zones],
            'selected_zone_id': order.delivery_zone_id.id if order and order.delivery_zone_id else None,
        }

