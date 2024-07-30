from odoo import http
from odoo.http import request, Response
import json
import logging

logger = logging.getLogger(__name__)

class InventoryController(http.Controller):

    @http.route('/api/create_receipt', type='json', auth='user', methods=['POST'])
    def create_receipt_api(self, **post):
        try:
            # Print the post data to the console for debugging
            logger.info("Received data: %s", post)

            StockPicking = request.env['stock.picking']
            StockMove = request.env['stock.move']
            products_data = post.get('products')
            partner_id = post.get('partner_id')
            location_id = post.get('location_id')
            location_dest_id = post.get('location_dest_id')
            tenant_id = post.get('tenant_id')
            site_code = post.get('site_code')
            picking_type_id = post.get('picking_type_id')

            # Validate the required fields
            if not all([partner_id, location_id, location_dest_id, products_data, picking_type_id]):
                logger.error("Missing required fields")
                return Response(json.dumps({'error': 'Missing required fields'}), status=400, content_type='application/json')

            # Check if picking_type_id exists in the database
            picking_type = request.env['stock.picking.type'].browse(picking_type_id)
            if not picking_type.exists():
                logger.error("Invalid picking_type_id: %s", picking_type_id)
                return Response(json.dumps({'error': 'Invalid picking_type_id'}), status=400, content_type='application/json')

            # Create a stock picking (receipt)
            picking_vals = {
                'partner_id': partner_id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'picking_type_id': picking_type_id,
                'move_type': 'direct',
                'tenant_id': tenant_id,
                'site_code': site_code,
            }
            picking = StockPicking.create(picking_vals)
            logger.info("Created picking: %s", picking)

            # Create stock moves for the products
            for product_data in products_data:
                product_id = product_data.get('product_id')
                product_uom_qty = product_data.get('product_uom_qty')

                if not all([product_id, product_uom_qty]):
                    logger.warning("Skipping product with missing fields: %s", product_data)
                    continue

                move_vals = {
                    'name': 'Receipt of %s' % request.env['product.product'].browse(product_id).name,
                    'product_id': product_id,
                    'product_uom_qty': product_uom_qty,
                    'product_uom': request.env['product.product'].browse(product_id).uom_id.id,
                    'picking_id': picking.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                }
                move = StockMove.create(move_vals)
                logger.info("Created move: %s", move)

            # Ensure stock moves are correctly associated
            picking.action_confirm()
            picking.action_assign()

            # Check the moves associated with the picking
            logger.info("Picking moves: %s", picking.move_ids_without_package)

            return Response(json.dumps({'success': True, 'receipt_id': picking.id}), content_type='application/json')

        except Exception as e:
            logger.error("Error creating receipt via API: %s", e)
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')
