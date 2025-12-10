# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import hmac
import hashlib
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class Sha6erWebhookController(http.Controller):
    """Webhook controller for Sha6er delivery updates"""

    @http.route('/smart/webhook/delivery', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def sha6er_webhook(self, **kwargs):
        """Handle Sha6er webhook for delivery status updates"""
        try:
            data = request.jsonrequest
            
            # Validate webhook signature (HMAC)
            # signature = request.httprequest.headers.get('X-Sha6er-Signature')
            # if not self._validate_signature(data, signature):
            #     return {'error': 'Invalid signature'}, 401
            
            shipment_id = data.get('shipment_id')
            status = data.get('status')
            tracking_number = data.get('tracking_number')
            
            if not shipment_id:
                return {'error': 'Missing shipment_id'}, 400
            
            # Find shipment
            shipment = request.env['sha6er.shipment'].sudo().search([
                ('sha6er_shipment_id', '=', shipment_id),
            ], limit=1)
            
            if not shipment:
                _logger.warning(f"Shipment not found: {shipment_id}")
                return {'error': 'Shipment not found'}, 404
            
            # Update shipment status
            status_mapping = {
                'accepted': 'accepted',
                'assigned': 'assigned',
                'picked_up': 'picked_up',
                'in_transit': 'in_transit',
                'delivered': 'delivered',
                'failed': 'failed',
            }
            
            if status in status_mapping:
                shipment.write({
                    'sha6er_status': status_mapping[status],
                    'sha6er_tracking_number': tracking_number or shipment.sha6er_tracking_number,
                    'courier_id': data.get('courier_id'),
                    'courier_name': data.get('courier_name'),
                    'pickup_date': data.get('pickup_date'),
                    'delivery_date': data.get('delivery_date'),
                })
                
                # Update picking if delivered
                if status == 'delivered':
                    shipment.picking_id.write({'state': 'done'})
                    if shipment.order_id:
                        shipment.order_id.write({'state': 'sale'})
            
            return {'success': True}
        except Exception as e:
            _logger.error(f"Error processing Sha6er webhook: {str(e)}")
            return {'error': str(e)}, 500
    
    def _validate_signature(self, data, signature):
        """Validate webhook signature using HMAC"""
        # Implementation depends on Sha6er's signature method
        # This is a placeholder
        return True

