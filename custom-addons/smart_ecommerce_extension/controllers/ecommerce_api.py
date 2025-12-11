# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

import json
import logging
from datetime import datetime
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class SmartEcommerceAPI(http.Controller):
    """REST API Controller for SMART eCommerce"""

    def _json_response(self, data, status=200):
        """Create JSON response with proper headers"""
        return request.make_response(
            json.dumps(data, default=str),
            headers=[
                ('Content-Type', 'application/json'),
                ('Cache-Control', 'no-store'),
            ],
            status=status
        )

    def _error_response(self, message, code='error', status=400):
        """Create error response"""
        return self._json_response({
            'success': False,
            'error': {
                'code': code,
                'message': message,
            }
        }, status=status)

    def _success_response(self, data=None, message=None):
        """Create success response"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return self._json_response(response)

    # ==========================================
    # PRODUCTS API
    # ==========================================

    @http.route('/smart/api/products', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_products(self, **kwargs):
        """
        Get products list with filters
        
        Query Parameters:
            - q: Search query (name/description)
            - brand: Filter by brand
            - category_id: Filter by category
            - price_min: Minimum price
            - price_max: Maximum price
            - availability: Filter by status (in_stock, low_stock, out_of_stock)
            - seller_id: Filter by seller
            - page: Page number (default: 1)
            - per_page: Items per page (default: 20, max: 100)
            - sort: Sort field (name, price, create_date)
            - order: Sort order (asc, desc)
        """
        try:
            domain = [('is_published', '=', True), ('sale_ok', '=', True)]
            
            # Search query
            if kwargs.get('q'):
                search_term = kwargs['q']
                domain.append('|')
                domain.append(('name', 'ilike', search_term))
                domain.append(('description', 'ilike', search_term))
            
            # Brand filter
            if kwargs.get('brand'):
                domain.append(('brand', '=', kwargs['brand']))
            
            # Category filter
            if kwargs.get('category_id'):
                domain.append(('public_categ_ids', 'in', [int(kwargs['category_id'])]))
            
            # Price range filter
            if kwargs.get('price_min'):
                domain.append(('list_price', '>=', float(kwargs['price_min'])))
            if kwargs.get('price_max'):
                domain.append(('list_price', '<=', float(kwargs['price_max'])))
            
            # Availability filter
            if kwargs.get('availability'):
                domain.append(('availability_status', '=', kwargs['availability']))
            
            # Seller filter (if marketplace_core installed)
            if kwargs.get('seller_id'):
                domain.append(('seller_id', '=', int(kwargs['seller_id'])))
            
            # Pagination
            page = max(1, int(kwargs.get('page', 1)))
            per_page = min(100, max(1, int(kwargs.get('per_page', 20))))
            offset = (page - 1) * per_page
            
            # Sorting
            sort_field = kwargs.get('sort', 'name')
            sort_order = kwargs.get('order', 'asc')
            valid_sorts = {'name', 'list_price', 'create_date', 'brand'}
            if sort_field not in valid_sorts:
                sort_field = 'name'
            order = f'{sort_field} {sort_order}'
            
            # Query
            Product = request.env['product.template'].sudo()
            total = Product.search_count(domain)
            products = Product.search(domain, limit=per_page, offset=offset, order=order)
            
            # Get available brands for filtering
            brands = Product.get_brands()
            
            return self._success_response({
                'products': [self._product_to_dict(p) for p in products],
                'filters': {
                    'brands': brands,
                },
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page,
                    'has_next': page * per_page < total,
                    'has_prev': page > 1,
                }
            })
            
        except Exception as e:
            _logger.error(f"Error in get_products: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    @http.route('/smart/api/products/<int:product_id>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_product(self, product_id, **kwargs):
        """Get single product details"""
        try:
            product = request.env['product.template'].sudo().browse(product_id)
            
            if not product.exists() or not product.is_published:
                return self._error_response(_('Product not found'), 'not_found', 404)
            
            return self._success_response(
                self._product_to_dict(product, detailed=True)
            )
            
        except Exception as e:
            _logger.error(f"Error in get_product: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    def _product_to_dict(self, product, detailed=False):
        """Convert product to dictionary for API response"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        
        data = {
            'id': product.id,
            'name': product.name,
            'brand': product.brand or None,
            'model': product.product_model or None,
            'price': product.list_price,
            'currency': product.currency_id.name,
            'availability_status': product.availability_status,
            'in_stock': product.availability_status != 'out_of_stock',
            'image_url': f'{base_url}/web/image/product.template/{product.id}/image_512' if product.image_512 else None,
            'image_hover_url': f'{base_url}/web/image/product.template/{product.id}/image_hover' if product.image_hover else None,
        }
        
        if detailed:
            delivery_info = product.get_estimated_delivery_date()
            data.update({
                'description': product.description_sale or product.description or '',
                'specifications': product.specifications or '',
                'video_url': product.video_url or None,
                'video_embed_url': product.get_video_embed_url() or None,
                'weight_kg': product.shipping_weight_kg or product.weight or 0.0,
                'category': {
                    'id': product.categ_id.id,
                    'name': product.categ_id.name,
                } if product.categ_id else None,
                'public_categories': [{
                    'id': cat.id,
                    'name': cat.name,
                } for cat in product.public_categ_ids],
                'qty_available': product.qty_available if product.is_storable else None,
                'delivery_estimate': delivery_info,
                'variants': [{
                    'id': v.id,
                    'name': v.display_name,
                    'price': v.lst_price,
                    'sku': v.default_code or None,
                    'qty_available': v.qty_available if product.is_storable else None,
                } for v in product.product_variant_ids],
            })
            
            # Add seller info if available
            if hasattr(product, 'seller_id') and product.seller_id:
                data['seller'] = {
                    'id': product.seller_id.id,
                    'name': product.seller_id.name,
                    'rating': product.seller_id.rating if hasattr(product.seller_id, 'rating') else 0.0,
                }
        
        return data

    # ==========================================
    # CART API
    # ==========================================

    @http.route('/smart/api/cart', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_cart(self, **kwargs):
        """Get current cart contents"""
        try:
            order = request.website.sale_get_order()
            if not order:
                return self._success_response({
                    'cart': None,
                    'items': [],
                    'total': 0,
                    'currency': request.website.currency_id.name,
                })
            
            return self._success_response(self._cart_to_dict(order))
            
        except Exception as e:
            _logger.error(f"Error in get_cart: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    @http.route('/smart/api/cart', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def update_cart(self, **kwargs):
        """
        Add/update cart items
        
        POST Body (JSON):
            - product_id: Product ID to add
            - quantity: Quantity (default: 1, use 0 to remove)
            - variant_id: Product variant ID (optional)
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else kwargs
            
            product_id = data.get('product_id')
            quantity = float(data.get('quantity', 1))
            variant_id = data.get('variant_id')
            
            if not product_id and not variant_id:
                return self._error_response(_('Product ID or variant ID required'), 'validation_error')
            
            # Get or create cart
            order = request.website.sale_get_order(force_create=True)
            
            # Find product variant
            if variant_id:
                product = request.env['product.product'].sudo().browse(int(variant_id))
            else:
                template = request.env['product.template'].sudo().browse(int(product_id))
                if not template.exists():
                    return self._error_response(_('Product not found'), 'not_found', 404)
                product = template.product_variant_id
            
            if not product.exists():
                return self._error_response(_('Product variant not found'), 'not_found', 404)
            
            # Find existing line
            existing_line = order.order_line.filtered(
                lambda l: l.product_id.id == product.id
            )
            
            if quantity <= 0:
                # Remove item
                if existing_line:
                    existing_line.unlink()
                    message = _('Item removed from cart')
                else:
                    message = _('Item not in cart')
            elif existing_line:
                # Update quantity
                existing_line.write({'product_uom_qty': quantity})
                message = _('Cart updated')
            else:
                # Add new item
                order.write({
                    'order_line': [(0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': quantity,
                        'name': product.display_name,
                    })]
                })
                message = _('Item added to cart')
            
            # Refresh order
            order = request.website.sale_get_order()
            
            return self._success_response(
                self._cart_to_dict(order),
                message=message
            )
            
        except json.JSONDecodeError:
            return self._error_response(_('Invalid JSON'), 'parse_error')
        except Exception as e:
            _logger.error(f"Error in update_cart: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    @http.route('/smart/api/cart/clear', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def clear_cart(self, **kwargs):
        """Clear all items from cart"""
        try:
            order = request.website.sale_get_order()
            if order:
                order.order_line.unlink()
            
            return self._success_response(message=_('Cart cleared'))
            
        except Exception as e:
            _logger.error(f"Error in clear_cart: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    def _cart_to_dict(self, order):
        """Convert sale order to cart dictionary"""
        items = []
        for line in order.order_line.filtered(lambda l: not l.is_delivery):
            items.append({
                'id': line.id,
                'product_id': line.product_id.product_tmpl_id.id,
                'variant_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'price_total': line.price_total,
                'image_url': f'/web/image/product.product/{line.product_id.id}/image_128',
            })
        
        # Get delivery info
        delivery_info = order.get_delivery_info() if hasattr(order, 'get_delivery_info') else {}
        
        return {
            'cart': {
                'id': order.id,
                'name': order.name,
                'state': order.state,
            },
            'items': items,
            'item_count': len(items),
            'subtotal': order.amount_untaxed,
            'tax': order.amount_tax,
            'total': order.amount_total,
            'currency': order.currency_id.name,
            'delivery': delivery_info,
        }

    # ==========================================
    # CHECKOUT API
    # ==========================================

    @http.route('/smart/api/checkout', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def checkout(self, **kwargs):
        """
        Process checkout
        
        POST Body (JSON):
            - shipping_address: {name, street, city, phone, email, country_code}
            - billing_address: (optional, same as shipping if not provided)
            - payment_method: Payment method code
            - notes: Order notes (optional)
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else kwargs
            
            order = request.website.sale_get_order()
            if not order or not order.order_line:
                return self._error_response(_('Cart is empty'), 'empty_cart')
            
            shipping = data.get('shipping_address', {})
            if not shipping.get('name') or not shipping.get('city'):
                return self._error_response(_('Shipping address required'), 'validation_error')
            
            # Create or update partner
            partner_vals = {
                'name': shipping.get('name'),
                'street': shipping.get('street', ''),
                'city': shipping.get('city', ''),
                'phone': shipping.get('phone', ''),
                'email': shipping.get('email', ''),
            }
            
            if shipping.get('country_code'):
                country = request.env['res.country'].sudo().search([
                    ('code', '=', shipping['country_code'].upper())
                ], limit=1)
                if country:
                    partner_vals['country_id'] = country.id
            
            # Find or create partner
            partner = None
            if shipping.get('email'):
                partner = request.env['res.partner'].sudo().search([
                    ('email', '=', shipping['email'])
                ], limit=1)
            
            if partner:
                partner.write(partner_vals)
            else:
                partner = request.env['res.partner'].sudo().create(partner_vals)
            
            # Update order
            order.write({
                'partner_id': partner.id,
                'partner_shipping_id': partner.id,
                'partner_invoice_id': partner.id,
                'note': data.get('notes', ''),
            })
            
            # Calculate delivery
            if order.delivery_zone_id:
                order._compute_delivery_info()
            
            # Validate stock
            stock_errors = []
            for line in order.order_line:
                if line.product_id.is_storable:
                    if line.product_id.qty_available < line.product_uom_qty:
                        stock_errors.append({
                            'product': line.product_id.name,
                            'requested': line.product_uom_qty,
                            'available': line.product_id.qty_available,
                        })
            
            if stock_errors:
                return self._error_response(
                    _('Some products are out of stock'),
                    'stock_error',
                    status=400
                )
            
            # Create checkout summary
            checkout_data = {
                'order_id': order.id,
                'order_ref': order.name,
                'partner': {
                    'id': partner.id,
                    'name': partner.name,
                    'email': partner.email,
                },
                'shipping_address': partner_vals,
                'items': [{
                    'name': line.name,
                    'quantity': line.product_uom_qty,
                    'price': line.price_total,
                } for line in order.order_line],
                'subtotal': order.amount_untaxed,
                'tax': order.amount_tax,
                'delivery_price': order.computed_delivery_price if hasattr(order, 'computed_delivery_price') else 0,
                'total': order.amount_total,
                'currency': order.currency_id.name,
                'estimated_delivery': order.estimated_delivery_date.isoformat() if hasattr(order, 'estimated_delivery_date') and order.estimated_delivery_date else None,
                'payment_url': f'/shop/payment',  # Redirect URL for payment
            }
            
            return self._success_response(checkout_data, message=_('Checkout ready'))
            
        except json.JSONDecodeError:
            return self._error_response(_('Invalid JSON'), 'parse_error')
        except Exception as e:
            _logger.error(f"Error in checkout: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    # ==========================================
    # PAYMENT CALLBACK API
    # ==========================================

    @http.route('/smart/api/payment/callback', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def payment_callback(self, **kwargs):
        """
        Payment gateway callback/webhook
        
        POST Body (JSON):
            - order_id: Odoo order ID
            - transaction_id: External transaction ID
            - status: Payment status (success, failed, pending)
            - amount: Payment amount
            - currency: Currency code
            - gateway: Payment gateway name
            - signature: HMAC signature for verification (optional)
            - metadata: Additional payment data
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else kwargs
            
            _logger.info(f"Payment callback received: {data}")
            
            order_id = data.get('order_id')
            transaction_id = data.get('transaction_id')
            status = data.get('status')
            amount = float(data.get('amount', 0))
            gateway = data.get('gateway', 'unknown')
            
            if not order_id or not status:
                return self._error_response(_('Missing required fields'), 'validation_error')
            
            # Find order
            order = request.env['sale.order'].sudo().browse(int(order_id))
            if not order.exists():
                return self._error_response(_('Order not found'), 'not_found', 404)
            
            # Verify amount matches (with tolerance)
            if amount > 0 and abs(amount - order.amount_total) > 0.01:
                _logger.warning(f"Payment amount mismatch: expected {order.amount_total}, got {amount}")
            
            # Process based on status
            if status == 'success':
                # Confirm order
                if order.state == 'draft':
                    order.action_confirm()
                
                # Log payment
                order.message_post(
                    body=_(
                        'Payment received via %(gateway)s<br/>'
                        'Transaction ID: %(txn_id)s<br/>'
                        'Amount: %(amount)s %(currency)s'
                    ) % {
                        'gateway': gateway,
                        'txn_id': transaction_id,
                        'amount': amount,
                        'currency': data.get('currency', order.currency_id.name),
                    }
                )
                
                return self._success_response({
                    'order_id': order.id,
                    'order_ref': order.name,
                    'status': 'confirmed',
                }, message=_('Payment processed successfully'))
                
            elif status == 'failed':
                order.message_post(
                    body=_(
                        'Payment failed via %(gateway)s<br/>'
                        'Transaction ID: %(txn_id)s<br/>'
                        'Reason: %(reason)s'
                    ) % {
                        'gateway': gateway,
                        'txn_id': transaction_id,
                        'reason': data.get('error_message', 'Unknown'),
                    }
                )
                
                return self._success_response({
                    'order_id': order.id,
                    'order_ref': order.name,
                    'status': 'payment_failed',
                }, message=_('Payment failed'))
                
            elif status == 'pending':
                order.message_post(
                    body=_(
                        'Payment pending via %(gateway)s<br/>'
                        'Transaction ID: %(txn_id)s'
                    ) % {
                        'gateway': gateway,
                        'txn_id': transaction_id,
                    }
                )
                
                return self._success_response({
                    'order_id': order.id,
                    'order_ref': order.name,
                    'status': 'pending',
                }, message=_('Payment pending'))
            
            else:
                return self._error_response(_('Invalid payment status'), 'validation_error')
            
        except json.JSONDecodeError:
            return self._error_response(_('Invalid JSON'), 'parse_error')
        except Exception as e:
            _logger.error(f"Error in payment_callback: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    # ==========================================
    # DELIVERY ZONES API
    # ==========================================

    @http.route('/smart/api/delivery/zones', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_delivery_zones(self, **kwargs):
        """Get available delivery zones"""
        try:
            zones = request.env['delivery.zone'].sudo().search([('active', '=', True)])
            
            return self._success_response({
                'zones': [{
                    'id': zone.id,
                    'name': zone.name,
                    'cities': zone.get_cities_list(),
                    'base_price': zone.base_price,
                    'extra_per_kg': zone.extra_price_per_kg,
                    'estimated_days': zone.get_delivery_estimate(),
                    'free_threshold': zone.free_delivery_threshold,
                    'currency': zone.currency_id.name,
                } for zone in zones],
                'all_cities': request.env['delivery.zone'].sudo().get_all_cities(),
            })
            
        except Exception as e:
            _logger.error(f"Error in get_delivery_zones: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

    @http.route('/smart/api/delivery/calculate', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def calculate_delivery(self, **kwargs):
        """
        Calculate delivery price
        
        POST Body (JSON):
            - city: Delivery city
            - weight_kg: Total weight in kg
            - order_total: Order total for free delivery check
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else kwargs
            
            city = data.get('city')
            weight_kg = float(data.get('weight_kg', 1.0))
            order_total = float(data.get('order_total', 0.0))
            
            if not city:
                return self._error_response(_('City is required'), 'validation_error')
            
            zone = request.env['delivery.zone'].sudo().find_zone_for_city(city)
            
            if not zone:
                return self._error_response(
                    _('No delivery available to this city'),
                    'no_coverage',
                    status=400
                )
            
            try:
                price = zone.compute_delivery_price(weight_kg, order_total)
            except ValidationError as e:
                return self._error_response(str(e), 'validation_error')
            
            return self._success_response({
                'zone': {
                    'id': zone.id,
                    'name': zone.name,
                },
                'price': price,
                'is_free': price == 0.0,
                'estimated_days': zone.get_delivery_estimate(),
                'currency': zone.currency_id.name,
            })
            
        except json.JSONDecodeError:
            return self._error_response(_('Invalid JSON'), 'parse_error')
        except Exception as e:
            _logger.error(f"Error in calculate_delivery: {str(e)}", exc_info=True)
            return self._error_response(str(e), 'server_error', 500)

