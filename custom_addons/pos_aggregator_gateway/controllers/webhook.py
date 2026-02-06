# import json
# import logging
# import hmac
# import hashlib
# from odoo import http
# from odoo.http import request

# _logger = logging.getLogger(__name__)


# class AggregatorController(http.Controller):

#     @http.route('/api/delivery/uber', type='http', auth='public', methods=['POST'], csrf=False)
#     def uber_webhook(self, **kwargs):
#         """
#         Secure Webhook for Uber Eats
#         1. Verify Signature (HMAC)
#         2. Map Uber Payload -> Odoo Schema
#         3. Create Order via POS API
#         """
#         try:
#             # 1️⃣ Get Configuration
#             config = request.env['pos.aggregator.config'].sudo().search([
#                 ('provider', '=', 'ubereats'),
#                 ('active', '=', True)
#             ], limit=1)
            
#             if not config:
#                 _logger.error("Uber Eats configuration not found or inactive")
#                 return request.make_response(
#                     json.dumps({'status': 'error', 'message': 'Configuration not found'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=500
#                 )
            
#             # 2️⃣ Security Check - HMAC Signature Verification
#             headers = request.httprequest.headers
#             signature = headers.get('X-Uber-Signature')
            
#             if not signature:
#                 _logger.warning("Uber Webhook: Missing X-Uber-Signature header")
#                 return request.make_response(
#                     json.dumps({'status': 'error', 'message': 'Forbidden: Missing Signature'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=403
#                 )
            
#             payload_bytes = request.httprequest.data
            
#             # ✅ CORRECT: Use webhook_signing_key (NOT client_secret!)
#             if not config.verify_webhook_signature(payload_bytes, signature):
#                 _logger.warning("Uber Webhook: Invalid Signature verification failed")
#                 return request.make_response(
#                     json.dumps({'status': 'error', 'message': 'Forbidden: Invalid Signature'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=403
#                 )
            
#             # 3️⃣ Parse & Map Payload
#             try:
#                 payload = json.loads(payload_bytes)
#             except Exception as e:
#                 _logger.error(f"Uber Webhook: Invalid JSON - {str(e)}")
#                 return request.make_response(
#                     json.dumps({'status': 'error', 'message': 'Invalid JSON body'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=400
#                 )
            
#             _logger.info(f"Uber Webhook received payload: {payload}")
            
#             # Support both direct payload and Event wrapper
#             order_data = payload.get('data', payload)
#             _logger.info(f"Uber Webhook order_data: {order_data}")
            
#             # Map to internal format
#             api_payload = self._map_uber_to_internal(order_data, config)
#             _logger.info(f"Uber Webhook api_payload: {api_payload}")
            
#             if not api_payload:
#                 _logger.info("Uber Webhook: Payload mapping resulted in empty data (ignored)")
#                 return request.make_response(
#                     json.dumps({'status': 'ignored', 'message': 'Not a valid order event'}),
#                     headers=[('Content-Type', 'application/json')],
#                     status=200
#                 )

#             # 4️⃣ Create POS Order
#             order = request.env['pos.order'].sudo().create_api_order(api_payload)
            
#             return request.make_response(
#                 json.dumps({
#                     'status': 'success',
#                     'order_id': order.id,
#                     'pos_ref': order.pos_reference
#                 }),
#                 headers=[('Content-Type', 'application/json')],
#                 status=200
#             )

#         except Exception as e:
#             _logger.exception("Uber Webhook Error")
#             return request.make_response(
#                 json.dumps({'status': 'error', 'message': str(e)}),
#                 headers=[('Content-Type', 'application/json')],
#                 status=500
#             )

#     def _verify_signature(self, body_bytes, signature, secret):
#         """ HMAC-SHA256 Signature Verification """
#         try:
#             expected = hmac.new(
#                 secret.encode('utf-8'),
#                 body_bytes,
#                 hashlib.sha256
#             ).hexdigest()
#             return hmac.compare_digest(signature, expected)
#         except Exception:
#             return False

#     def _map_uber_to_internal(self, data, config):
#         """ Maps Uber JSON to our internal create_api_order Schema """
        
#         # Uber Structure can be a notification or a full order
#         # For this integration we facilitate the "Full Order" webhook payload
        
#         # 1. Identify Items
#         items = data.get('cart', {}).get('items', []) or data.get('items', [])
#         if not items:
#             return None

#         # 2. Map Lines
#         order_lines = []
#         Product = request.env['product.product'].sudo()
        
#         for item in items:
#             ext_id = item.get('external_id') or item.get('id')
#             qty = item.get('quantity', 1)
#             # Uber price is usually cents, but our curl tests might send units.
#             # We trust the price sent or product price fallback?
#             # Standard: Uber sends unit price in 'price' field.
#             price = item.get('price', 0)
            
#             # Find Product
#             prod = Product.search([('default_code', '=', ext_id)], limit=1)
#             if not prod:
#                 prod = Product.search([('uber_eats_id', '=', ext_id)], limit=1)
            
#             if not prod:
#                 _logger.warning(f"Product not found for external_id: {ext_id}")
#                 continue
                
#             order_lines.append({
#                 'product_id': prod.id,
#                 'qty': qty,
#                 'price_unit': price / 100 if price > 1000 and isinstance(price, int) else price,
#             })
            
#         if not order_lines:
#              return None

#         # 3. Customer & Address
#         eater = data.get('eater', {})
#         customer_name = f"{eater.get('first_name', '')} {eater.get('last_name', '')}".strip() or "Uber Eater"
#         customer_phone = eater.get('phone', '')
        
#         address_data = data.get('delivery_address', {})
#         address_parts = [
#             address_data.get('address_line', ''),
#             address_data.get('city', ''),
#             address_data.get('state', ''),
#             address_data.get('zip', '')
#         ]
#         delivery_address = ", ".join([p for p in address_parts if p])

#         # 4. Resolve Relations
#         # We need the POS session to check allowed payment methods
#         session = request.env['pos.session'].sudo().search([
#             ('state', '=', 'opened'),
#             ('delivery_active', '=', True),
#             ('config_id.accept_remote_orders', '=', True)
#         ], limit=1)
        
#         if not session:
#             return None # No active session to handle this
            
#         fp_id = False
#         FiscalPos = request.env['account.fiscal.position'].sudo()
#         fp = FiscalPos.search([('name', 'ilike', 'Delivery')], limit=1)
#         if fp:
#             fp_id = fp.id
            
#         PaymentMethod = request.env['pos.payment.method'].sudo()
#         pm = PaymentMethod.search([
#             ('name', 'ilike', 'Uber'),
#             ('id', 'in', session.config_id.payment_method_ids.ids)
#         ], limit=1)
#         if not pm:
#             # Fallback to the first available method in the config
#             pm = session.config_id.payment_method_ids[:1]

#         # 5. Construct Payload
#         return {
#             'uuid': data.get('id') or data.get('uuid'),
#             'source': 'uber',
#             'amount_paid': data.get('total_price') or data.get('total') or 0,
#             'payment_method_id': pm.id if pm else False,
#             'lines': order_lines,
#             'fiscal_position_id': fp_id,
#             'customer_name': customer_name,
#             'customer_phone': customer_phone,
#             'delivery_address': delivery_address,
#             'notes': data.get('special_instructions', '') or data.get('notes', ''),
#         }

import json
import logging
import hmac
import hashlib
from odoo import http
from odoo.http import request
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AggregatorController(http.Controller):

    @http.route('/api/delivery/uber', type='http', auth='public', methods=['POST'], csrf=False)
    def uber_webhook(self, **kwargs):
        """
        Secure Webhook for Uber Eats
        1. Verify Signature (HMAC using webhook_signing_key)
        2. Map Uber Payload -> Odoo Schema
        3. Create Order via POS API
        """
        try:
            # 1️⃣ Get Configuration
            config = request.env['pos.aggregator.config'].sudo().search([
                ('provider', '=', 'ubereats'),
                ('active', '=', True)
            ], limit=1)
            
            if not config:
                _logger.error("Uber Eats configuration not found or inactive")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Configuration not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
            
            # 2️⃣ Security Check - HMAC Signature Verification
            headers = request.httprequest.headers
            signature = headers.get('X-Uber-Signature')
            
            if not signature:
                _logger.warning("Uber Webhook: Missing X-Uber-Signature header")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Forbidden: Missing Signature'}),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )
            
            payload_bytes = request.httprequest.data
            
            # ✅ CORRECT: Use webhook_signing_key (NOT client_secret!)
            if not self._verify_webhook_signature(payload_bytes, signature, config.webhook_signing_key):
                _logger.warning("Uber Webhook: Invalid Signature verification failed")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Forbidden: Invalid Signature'}),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )
            
            _logger.info("Uber Webhook: Signature validated successfully")
            
            # 3️⃣ Parse & Map Payload
            try:
                payload = json.loads(payload_bytes)
            except Exception as e:
                _logger.error(f"Uber Webhook: Invalid JSON - {str(e)}")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Invalid JSON body'}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            _logger.info(f"Uber Webhook received payload: {payload}")
            
            # Support both direct payload and Event wrapper
            order_data = payload.get('data', payload)
            _logger.info(f"Uber Webhook order_data: {order_data}")
            
            # Map to internal format
            api_payload = self._map_uber_to_internal(order_data, config)
            _logger.info(f"Uber Webhook api_payload: {api_payload}")
            
            if not api_payload:
                _logger.info("Uber Webhook: Payload mapping resulted in empty data (ignored)")
                return request.make_response(
                    json.dumps({'status': 'ignored', 'message': 'Not a valid order event'}),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )

            # 4️⃣ Create POS Order
            order = request.env['pos.order'].sudo().create_api_order(api_payload)
            
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'order_id': order.id,
                    'pos_ref': order.pos_reference
                }),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            _logger.exception("Uber Webhook Error")
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )


    @http.route('/uber/oauth/callback', type='http', auth='public', methods=['GET'], csrf=False)
    def uber_oauth_callback(self, code=None, error=None, **kwargs):
        """
        OAuth 2.0 Callback Handler for Uber Eats
        Receives authorization code and exchanges it for access token
        """
        try:
            if error:
                _logger.error(f"Uber OAuth Error: {error}")
                return request.render('http_routing.404', {
                    'message': f'Authorization failed: {error}'
                })
            
            if not code:
                _logger.error("Uber OAuth: No authorization code received")
                return request.render('http_routing.404', {
                    'message': 'No authorization code provided'
                })
            
            # Get configuration
            config = request.env['pos.aggregator.config'].sudo().search([
                ('provider', '=', 'ubereats'),
                ('active', '=', True)
            ], limit=1)
            
            if not config:
                _logger.error("Uber Eats configuration not found")
                return request.render('http_routing.404', {
                    'message': 'Configuration not found'
                })
            
            # Exchange authorization code for access token
            token_url = 'https://login.uber.com/oauth/v2/token'
            
            token_data = {
                'client_id': config.client_id,
                'client_secret': config.client_secret,
                'grant_type': 'authorization_code',
                'redirect_uri': 'https://demo.primetek.in/uber/oauth/callback',
                'code': code
            }
            
            _logger.info(f"Exchanging authorization code for access token")
            
            response = requests.post(token_url, data=token_data)
            
            if response.status_code != 200:
                _logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return request.render('http_routing.404', {
                    'message': f'Token exchange failed: {response.text}'
                })
            
            token_response = response.json()
            access_token = token_response.get('access_token')
            refresh_token = token_response.get('refresh_token')
            expires_in = token_response.get('expires_in', 2592000)  # Default 30 days
            
            # Calculate expiry time
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Store tokens in configuration
            config.sudo().write({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            _logger.info(f"OAuth tokens stored successfully. Expires at: {expires_at}")
            
            # Redirect to success page or back to Odoo
            return request.redirect('/web#action=pos_aggregator_gateway.action_pos_aggregator_config')

        except Exception as e:
            _logger.exception("OAuth Callback Error")
            return request.render('http_routing.404', {
                'message': f'OAuth error: {str(e)}'
            })


    def _verify_webhook_signature(self, body_bytes, signature, signing_key):
        """
        HMAC-SHA256 Signature Verification using Webhook Signing Key
        
        IMPORTANT: This uses webhook_signing_key, NOT client_secret!
        Uber has separate keys for:
        - client_secret: OAuth API authentication
        - signing_key: Webhook signature verification
        """
        try:
            if not signing_key:
                _logger.error("Webhook signing key not configured")
                return False
                
            expected = hmac.new(
                signing_key.encode('utf-8'),
                body_bytes,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature.lower(), expected.lower())
        except Exception as e:
            _logger.error(f"Signature verification error: {str(e)}")
            return False


    def _map_uber_to_internal(self, data, config):
        """ Maps Uber JSON to our internal create_api_order Schema """
        
        # Uber Structure can be a notification or a full order
        # For this integration we facilitate the "Full Order" webhook payload
        
        # 1. Identify Items
        items = data.get('cart', {}).get('items', []) or data.get('items', [])
        if not items:
            return None

        # 2. Map Lines
        order_lines = []
        Product = request.env['product.product'].sudo()
        
        for item in items:
            ext_id = item.get('external_id') or item.get('id')
            qty = item.get('quantity', 1)
            # Uber price is usually cents, but our curl tests might send units.
            # We trust the price sent or product price fallback?
            # Standard: Uber sends unit price in 'price' field.
            price = item.get('price', 0)
            
            # Find Product
            prod = Product.search([('default_code', '=', ext_id)], limit=1)
            if not prod:
                prod = Product.search([('uber_eats_id', '=', ext_id)], limit=1)
            
            if not prod:
                _logger.warning(f"Product not found for external_id: {ext_id}")
                continue
                
            order_lines.append({
                'product_id': prod.id,
                'qty': qty,
                'price_unit': price / 100 if price > 1000 and isinstance(price, int) else price,
            })
            
        if not order_lines:
            return None

        # 3. Customer & Address
        eater = data.get('eater', {})
        customer_name = f"{eater.get('first_name', '')} {eater.get('last_name', '')}".strip() or "Uber Eater"
        customer_phone = eater.get('phone', '')
        
        address_data = data.get('delivery_address', {})
        address_parts = [
            address_data.get('address_line', ''),
            address_data.get('city', ''),
            address_data.get('state', ''),
            address_data.get('zip', '')
        ]
        delivery_address = ", ".join([p for p in address_parts if p])

        # 4. Resolve Relations
        # We need the POS session to check allowed payment methods
        session = request.env['pos.session'].sudo().search([
            ('state', '=', 'opened'),
            ('delivery_active', '=', True),
            ('config_id.accept_remote_orders', '=', True)
        ], limit=1)
        
        if not session:
            _logger.error("No active POS session available for remote orders")
            return None
            
        fp_id = False
        FiscalPos = request.env['account.fiscal.position'].sudo()
        fp = FiscalPos.search([('name', 'ilike', 'Delivery')], limit=1)
        if fp:
            fp_id = fp.id
            
        PaymentMethod = request.env['pos.payment.method'].sudo()
        pm = PaymentMethod.search([
            ('name', 'ilike', 'Uber'),
            ('id', 'in', session.config_id.payment_method_ids.ids)
        ], limit=1)
        if not pm:
            # Fallback to the first available method in the config
            pm = session.config_id.payment_method_ids[:1]

        # 5. Construct Payload
        return {
            'uuid': data.get('id') or data.get('uuid'),
            'source': 'uber',
            'amount_paid': data.get('total_price') or data.get('total') or 0,
            'payment_method_id': pm.id if pm else False,
            'lines': order_lines,
            'fiscal_position_id': fp_id,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'delivery_address': delivery_address,
            'notes': data.get('special_instructions', '') or data.get('notes', ''),
        }
