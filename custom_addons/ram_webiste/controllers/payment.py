import pprint
import werkzeug

from odoo import http, _
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
import logging
import json

_logger = logging.getLogger(__name__)

class RamPaymentController(http.Controller):
    
    @http.route('/ram/payment/providers', type='json', auth='public')
    def get_providers(self):
        """ Return available payment providers for configuration """
        providers = request.env['payment.provider'].sudo().search([
            ('state', '!=', 'disabled'),
            ('company_id', '=', request.env.company.id)
        ])
        return [{
            'id': p.id,
            'name': p.name,
            'code': p.code,
            'image_url': f"/web/image/payment.provider/{p.id}/image_128",
            'inline_form_view_id': p.inline_form_view_id.id if p.inline_form_view_id else False
        } for p in providers]

    @http.route('/ram/payment/transaction/create', type='json', auth='public')
    def create_transaction(self, amount, provider_id, currency_id=False, partner_id=False, flow='direct'):
        # 1. Validate inputs
        if not amount or not provider_id:
             return {'error': 'Invalid parameters'}
             
        provider = request.env['payment.provider'].sudo().browse(int(provider_id))
        if not provider.exists():
             return {'error': 'Provider not found'}
             
        # 2. Get Partner
        if not partner_id:
            partner = request.env.user.partner_id
            if not partner or request.env.user._is_public():
                 # For payment, we generally need a partner
                 # If user is public, we might need to create one or use a "Guest" logic
                 # But our ordering flow requires login for checkout (enforced in main.py)
                 return {'error': 'Partner required'}
    @http.route('/ram/payment/get_url', type='json', auth='user')
    def get_payment_url(self, amount, currency_id=False):
        """
        Generates a signed URL for the standard Odoo payment page.
        This allows us to leverage Odoo's built-in Stripe Elements/Form support
        without re-implementing it in our custom frontend.
        """
        user = request.env.user
        partner = user.partner_id
        
        # Ensure currency
        if not currency_id:
            currency_id = request.env.company.currency_id.id
            
        currency = request.env['res.currency'].browse(int(currency_id))
        
        # Generate Reference
        reference = request.env['payment.transaction'].sudo()._compute_reference('stripe', prefix='RAM-WEB')
        
        # Generate Access Token for /payment/pay
        # Signature: partner_id, amount, currency_id
        from odoo.addons.payment import utils as payment_utils
        access_token = payment_utils.generate_access_token(partner.id, float(amount), currency.id)
        
        # Construct URL
        # We pass the reference so the user pays for THIS specific reference.
        # When they return, we find the transaction by this reference.
        base_url = user.get_base_url()
        query = {
            'reference': reference,
            'amount': float(amount),
            'currency_id': currency.id,
            'partner_id': partner.id,
            'access_token': access_token,
            'company_id': request.env.company.id,
        }
        from werkzeug.urls import url_encode
        return {
            'url': f"/payment/pay?{url_encode(query)}",
            'reference': reference
        }

    @http.route('/ram/payment/finalize', type='http', auth='user', website=True)
    def ram_finalize_payment(self, reference, **kwargs):
        """
        Called after successful payment.
        1. Verify Transaction is successful.
        2. Create POS Order from Cart.
        3. Link Transaction.
        4. Redirect to Status.
        """
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)
        
        # Allow 'authorized' (capturing), 'done' (captured), 'pending' (wire transfer etc)
        # For Food, we usually want at least authorized.
        if not tx:
             return request.render('website.http_error', {
                'status_code': 'Payment Error',
                'status_message': 'Transaction not found.'
            })
            
        if tx.state not in ['done', 'authorized', 'pending']:
            # If rejected/error
            return request.redirect('/ram?error=payment_failed')
            
        # Reconstruct Order from Cart
        # We need the user from the transaction if possible, or current user
        # Since this is a redirect, current user should be the one who paid (if logged in)
        cart = request.env['ram.website.cart'].sudo().get_cart_for_partner(request.env.user.partner_id.id)
        
        # Idempotency: Check if order already exists for this reference
        # (refreshing the finalize page shouldn't duplicate orders)
        existing = request.env['pos.order'].sudo().search([('pos_reference', '=', reference)], limit=1)
        if existing:
             return request.redirect(f'/ram/order/status/{existing.unique_uuid}')

        if not cart or not cart.line_ids:
             return request.redirect('/ram?error=cart_empty_after_payment')

        # Convert Cart to Order Data
        lines = []
        for line in cart.line_ids:
            variation_data = json.loads(line.variation_data) if line.variation_data else {}
            lines.append({
                "product_id": line.product_id.id,
                "qty": line.qty,
                "price": line.price_unit,
                "attribute_value_ids": variation_data.get("attribute_value_ids", []),
                "combo_line_ids": variation_data.get("combo_line_ids", []),
                "note": line.customer_note,
            })

        order_data = {
            'lines': lines,
            'partner_id': request.env.user.partner_id.id,
            'amount_paid': tx.amount,
            'customer_name': request.env.user.partner_id.name,
            'customer_phone': request.env.user.partner_id.phone,
            'customer_email': request.env.user.partner_id.email,
            'payment_method': 'online',
            'transaction_reference': reference, 
            'uuid': reference, 
        }
        
        try:
             # Reuse main logic steps
             session = request.env['pos.session'].sudo().search([
                ('state', '=', 'opened'),
                ('delivery_active', '=', True),
                ('config_id.accept_remote_orders', '=', True)
             ], limit=1)
             
             if not session:
                 return request.render('website.http_error', {'status_code': 'Ordered Failed', 'status_message': 'No active POS session.'})

             # Find 'Online' Payment Method
             pm = session.config_id.payment_method_ids.filtered(lambda m: 'card' in m.name.lower() and not m.use_payment_terminal)[:1]
             if not pm: pm = session.config_id.payment_method_ids[:1]
             
             order_data['payment_method_id'] = pm.id
             order_data['session_id'] = session.id
             order_data['source'] = 'native_web'
             
             # Create Order
             order = request.env['pos.order'].sudo().create_api_order(order_data)
             
             # 1. GENERATE INVOICE
             try:
                 order.action_pos_order_invoice()
                 # Ensure invoice is compliant/open if needed, usually action_pos_order_invoice does it.
                 # order.account_move is the invoice.
             except Exception as inv_e:
                 _logger.error(f"Failed to generate invoice for order {order.name}: {inv_e}")

             # 2. TRIGGER POS NOTIFICATION
             # Determine channel. For Odoo 16+, typically 'pos_config' channel.
             # We send a message so the POS client (if customized to listen) or just the bus picks it up.
             # 'pos_order_api' might allow polling, but we force a bus message for "Real Time" feel.
             # Channel: request.env['pos.config'].browse(session.config_id.id)._get_bus_channel()
             # Payload: 'RAM_ORDER_NEW'
             try:
                 # Check if we can get channel
                 channel = session.config_id._get_bus_channel() if hasattr(session.config_id, '_get_bus_channel') else None
                 if channel:
                     request.env['bus.bus']._sendone(channel, 'RAM_ORDER_NEW', {
                         'order_id': order.id, 
                         'ref': order.pos_reference,
                         'amount': order.amount_total
                     })
             except Exception as bus_e:
                 _logger.error(f"Bus Notification Failed: {bus_e}")

             # 3. Clean Cart
             cart.line_ids.unlink()
             
             # 4. Redirect to SUCCESS Page (Not Status Page)
             return request.redirect(f'/ram/order/success/{order.unique_uuid}')
             
        except Exception as e:
            _logger.exception("Finalize Failed")
            return request.render('website.http_error', {
                'status_code': 'Order Creation Failed', 
                'status_message': str(e)
            })

    @http.route('/ram/order/success/<string:uuid>', type='http', auth='public', website=True)
    def ram_order_success_page(self, uuid, **kwargs):
        order = request.env['pos.order'].sudo().search([('unique_uuid', '=', uuid)], limit=1)
        if not order:
            return request.redirect('/ram')
            
        return request.render('ram_webiste.ram_order_success_page', {'order': order})

    @http.route('/ram/payment/transaction/result', type='json', auth='public')
    def payment_result(self, reference):
         # Check status
         tx = request.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)
         if not tx:
              return {'error': 'Transaction not found'}
              
         return {
             'state': tx.state, # 'draft', 'pending', 'authorized', 'done', 'cancel', 'error'
             'is_post_processed': tx.is_post_processed,
             'last_state_change': str(tx.last_state_change),
         }
