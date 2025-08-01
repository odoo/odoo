from odoo import http
from odoo.http import request
import logging

logger = logging.getLogger(__name__)

class QuotationController(http.Controller):

    @http.route('/api/add_quotation', type='json', auth='user', methods=['POST'])
    def add_quotation(self, **post):
        
        logger.info(f"Received data: {post}")
        
        partner_id = post.get('partner_id')
        order_lines = post.get('order_lines')
        delivery_details = post.get('delivery_details', {})

        if not partner_id:
            logger.error("Partner ID is missing")
            return {
                'error': 'Partner ID is missing'
            }

        if not order_lines:
            logger.error("Order lines are missing")
            return {
                'error': 'Order lines are missing'
            }

        try:
            # Ensure order_lines is a list
            if not isinstance(order_lines, list):
                logger.error("Order lines should be a list")
                return {
                    'error': 'Order lines should be a list'
                }

            # Create the sale order
            order = request.env['sale.order'].sudo().create({
                'partner_id': partner_id,
                'order_line': [(0, 0, {
                    'product_id': line['product_id'],
                    'product_uom_qty': line['quantity'],
                    'price_unit': line.get('price_unit', 0.0)
                }) for line in order_lines],
                'customer_name': delivery_details.get('name', ''),
                'customer_address': delivery_details.get('address', ''),
                'customer_suburb': delivery_details.get('suburb', ''),
                'customer_state': delivery_details.get('state', ''),
                'customer_postcode': delivery_details.get('postcode', ''),
                'customer_email': delivery_details.get('email', ''),
                'customer_phone': delivery_details.get('phone_number', ''),
            })


            logger.info(f"Created quotation: {order.name}")

            return {
                'success': True,
                'quotation_id': order.id,
                'quotation_name': order.name
            }

        except Exception as e:
            logger.error(f"Error creating quotation: {e}")
            return {
                'error': str(e)
            }
