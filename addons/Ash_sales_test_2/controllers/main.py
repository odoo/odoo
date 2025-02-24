from odoo import http
from odoo.http import request
import logging

logger = logging.getLogger(__name__)

class QuotationController(http.Controller):

    @http.route('/api/add_order', type='json', auth='user', methods=['POST'])
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

            order_lines_data = []
            for line in order_lines:
                default_code = line.get('default_code')
                if not default_code:
                    logger.error("Default code is missing for a product line")
                    return {
                        'error': 'Default code is missing for a product line'
                    }

                # Search for the product using default_code
                product = request.env['product.product'].sudo().search([('default_code', '=', default_code)], limit=1)
                if not product:
                    logger.error(f"Product with default code {default_code} not found")
                    return {
                        'error': f'Product with default code {default_code} not found'
                    }

                # Add product line data
                order_lines_data.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': line.get('quantity', 1.0),
                    'price_unit': line.get('price_unit', 0.0)
                }))

            # Create the sale order
            order = request.env['sale.order'].sudo().create({
                'partner_id': partner_id,
                'order_line': order_lines_data,
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
