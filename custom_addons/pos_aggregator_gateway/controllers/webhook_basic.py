import os
import base64
import json
import logging
import hmac
import hashlib
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class AggregatorController(http.Controller):

    @http.route('/api/delivery/uber', type='http', auth='public', methods=['POST'], csrf=False)
    def uber_webhook(self, **kwargs):
        """
        Secure Webhook for Uber Eats
        1. Verify Basic Auth (if configured)
        2. Verify Signature (HMAC)
        3. Map Uber Payload -> Odoo Schema
        4. Create Order via POS API
        """
        try:
            headers = request.httprequest.headers
            
            # 1️⃣ Basic Auth Check (Optional Layer)
            basic_user = os.getenv('UBER_WEBHOOK_BASIC_USER')
            basic_pass = os.getenv('UBER_WEBHOOK_BASIC_PASSWORD')
            
            if basic_user and basic_pass:
                auth_header = headers.get('Authorization', '')
                
                if not auth_header.startswith('Basic '):
                    _logger.warning("Uber Webhook: Missing Basic Auth header")
                    return request.make_response(
                        json.dumps({'status': 'error', 'message': 'Unauthorized: Missing Basic Auth'}),
                        headers=[('Content-Type', 'application/json')],
                        status=401
                    )
                
                try:
                    # Decode Basic Auth
                    encoded_creds = auth_header.replace('Basic ', '')
                    decoded = base64.b64decode(encoded_creds).decode('utf-8')
                    username, password = decoded.split(':', 1)
                    
                    if username != basic_user or password != basic_pass:
                        _logger.warning(f"Uber Webhook: Invalid Basic Auth - got username: {username}")
                        return request.make_response(
                            json.dumps({'status': 'error', 'message': 'Unauthorized: Invalid credentials'}),
                            headers=[('Content-Type', 'application/json')],
                            status=401
                        )
                    
                    _logger.info("Uber Webhook: Basic Auth validated successfully")
                    
                except Exception as e:
                    _logger.error(f"Uber Webhook: Basic Auth parsing error: {e}")
                    return request.make_response(
                        json.dumps({'status': 'error', 'message': 'Unauthorized: Auth header malformed'}),
                        headers=[('Content-Type', 'application/json')],
                        status=401
                    )
            
            # 2️⃣ Signature Verification
            signature = headers.get('X-Uber-Signature')
            config = request.env['pos.aggregator.config'].sudo().search([
                ('provider', '=', 'ubereats'),
                ('active', '=', True)
            ], limit=1)
            
            if config and config.client_secret:
                if not signature:
                    _logger.warning("Uber Webhook: Missing X-Uber-Signature header")
                    return request.make_response(
                        json.dumps({'status': 'error', 'message': 'Forbidden: Missing Signature'}),
                        headers=[('Content-Type', 'application/json')],
                        status=403
                    )
                
                payload_bytes = request.httprequest.data
                if not self._verify_signature(payload_bytes, signature, config.client_secret):
                    _logger.warning("Uber Webhook: Invalid Signature verification failed")
                    return request.make_response(
                        json.dumps({'status': 'error', 'message': 'Forbidden: Invalid Signature'}),
                        headers=[('Content-Type', 'application/json')],
                        status=403
                    )
                
                _logger.info("Uber Webhook: Signature validated successfully")
            
            # 3️⃣ Parse & Map Payload
            try:
                payload = json.loads(request.httprequest.data)
            except Exception:
                 return request.make_response(
                     json.dumps({'status': 'error', 'message': 'Invalid JSON body'}), 
                     headers=[('Content-Type', 'application/json')],
                     status=400
                 )
            
            _logger.info(f"Uber Webhook received payload: {payload}")
            
            # Support both direct payload (test/curl) and Event wrapper
            order_data = payload.get('data', payload) 
            _logger.info(f"Uber Webhook order_data: {order_data}")
            
            # Internalize
            api_payload = self._map_uber_to_internal(order_data, config)
            _logger.info(f"Uber Webhook api_payload: {api_payload}")
            
            if not api_payload:
                 _logger.info("Uber Webhook: Payload mapping resulted in empty data (ignored)")
                 return request.make_response(
                     json.dumps({'status': 'ignored', 'message': 'Not a valid order event'}),
                     headers=[('Content-Type', 'application/json')],
                     status=200
                 )

            # 4️⃣ Inject into POS
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

    # Keep your existing _verify_signature and _map_uber_to_internal methods unchanged
