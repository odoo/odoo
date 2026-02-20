# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class PosOrderApiController(http.Controller):

    @http.route('/api/pos/order/create', type='jsonrpc', auth='user', methods=['POST'])
    def create_order(self, **params):
        """
        Internal JSON-RPC 2.0 endpoint for creating orders.
        Requires authenticated session.
        """
        try:
            order = request.env['pos.order'].create_api_order(params)
            return {
                'status': 'success',
                'order_id': order.id,
                'pos_ref': order.pos_reference
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/pos/session/status', type='jsonrpc', auth='user', methods=['POST'])
    def session_status(self, config_id=False):
        """ Check if a specific or any delivery session is active """
        domain = [('state', '=', 'opened')]
        if config_id:
            domain.append(('config_id', '=', config_id))
        
        session = request.env['pos.session'].search(domain, limit=1)
        if not session:
            return {'status': 'inactive', 'message': 'No open session found'}
            
        return {
            'status': 'active',
            'session_id': session.id,
            'delivery_active': session.delivery_active and session.config_id.accept_remote_orders,
            'config_name': session.config_id.name
        }
