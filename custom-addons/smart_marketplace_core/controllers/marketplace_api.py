# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)


class MarketplaceAPIController(http.Controller):
    """REST API Controller for Marketplace"""

    @http.route('/smart/api/products', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_products(self, **kwargs):
        """Get products list with filters"""
        try:
            domain = [('marketplace_published', '=', True), ('marketplace_approved', '=', True)]
            
            # Filters
            if kwargs.get('q'):
                domain.append(('name', 'ilike', kwargs['q']))
            if kwargs.get('category_id'):
                domain.append(('categ_id', '=', int(kwargs['category_id'])))
            if kwargs.get('seller_id'):
                domain.append(('seller_id', '=', int(kwargs['seller_id'])))
            if kwargs.get('price_min'):
                domain.append(('list_price', '>=', float(kwargs['price_min'])))
            if kwargs.get('price_max'):
                domain.append(('list_price', '<=', float(kwargs['price_max'])))
            if kwargs.get('in_stock') == 'true':
                domain.append(('availability_status', '!=', 'out_of_stock'))
            
            # Pagination
            page = int(kwargs.get('page', 1))
            per_page = int(kwargs.get('per_page', 20))
            offset = (page - 1) * per_page
            
            products = request.env['product.template'].sudo().search(domain, limit=per_page, offset=offset)
            total = request.env['product.template'].sudo().search_count(domain)
            
            result = {
                'data': [self._product_to_dict(p) for p in products],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page,
                }
            }
            
            return request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error in get_products: {str(e)}")
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/smart/api/products/<int:product_id>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_product(self, product_id, **kwargs):
        """Get single product details"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists() or not product.marketplace_published:
                return request.make_response(
                    json.dumps({'error': 'Product not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            result = self._product_to_dict(product, detailed=True)
            return request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Error in get_product: {str(e)}")
            return request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    def _product_to_dict(self, product, detailed=False):
        """Convert product to dictionary"""
        data = {
            'id': product.id,
            'name': product.name,
            'description': product.description or '',
            'price': product.list_price,
            'currency': product.currency_id.name if product.currency_id else 'USD',
            'image_url': f'/web/image/product.template/{product.id}/image_128' if product.image_128 else None,
            'seller': {
                'id': product.seller_id.id if product.seller_id else None,
                'name': product.seller_id.name if product.seller_id else None,
                'rating': product.seller_id.rating if product.seller_id else 0.0,
            } if product.seller_id else None,
            'availability_status': product.availability_status,
            'in_stock': product.availability_status != 'out_of_stock',
        }
        
        if detailed:
            data.update({
                'description_sale': product.description_sale or '',
                'weight': product.weight,
                'shipping_weight_kg': product.shipping_weight_kg,
                'qty_available': product.qty_available if product.type == 'product' else None,
                'category': {
                    'id': product.categ_id.id if product.categ_id else None,
                    'name': product.categ_id.name if product.categ_id else None,
                } if product.categ_id else None,
                'variants': [{
                    'id': v.id,
                    'name': v.name,
                    'price': v.list_price,
                    'qty_available': v.qty_available if product.type == 'product' else None,
                } for v in product.product_variant_ids],
            })
        
        return data

