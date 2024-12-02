from odoo import models, fields, api
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_released = fields.Selection([
        ('unpicked', 'Unpicked'),
        ('released', 'Released'),
        ('unreleased', 'Unreleased')
    ], string="Is Released", default='unpicked')

    pick_status = fields.Selection([
        ('picked', 'Picked'),
        ('packed', 'Packed'),
        ('none', 'None')
    ], string="Pick Status", default='none')
    
    # New fields
    consignment_number = fields.Char(string="Consignment Number")
    carrier = fields.Char(string="Carrier")
    status = fields.Char(string="Status")
    tracking_url = fields.Char(string="Tracking URL")

    def action_release_quotations(self):
        logger.info(f"action_release_quotations called with {len(self)} orders")
        if not self:
            logger.warning("No orders passed to action_release_quotations")
        for order in self:
            logger.info(f"Processing order: {order.name}")
            all_products_available = True
            products_data = []

            # Fetch picking records for the current order
            picking_records = self.env['stock.picking'].search([
                ('origin', '=', order.name),
                ('state', '!=', 'cancel')  # Exclude canceled pickings
            ])
            # Filter only "pick" type pickings
            pick_only_picking_records = picking_records.filtered(
                lambda p: 'Pick' in p.picking_type_id.name  # Adjust logic based on your type naming convention
            )
            
            for line in order.order_line:
                product_qty = line.product_uom_qty  
                product = line.product_id

                # Search for the product using its default_code
                product_default_code = product.default_code

                # Initialize available_qty to 0; it will be updated based on location-specific quant
                available_qty = 0

                # Fetch the stock move related to this order line and picking
                stock_moves = self.env['stock.move'].search([
                    ('sale_line_id', '=', line.id),
                    ('picking_id', 'in', picking_records.ids),
                    ('state', 'not in', ['cancel', 'done'])  # Ensure the move is active
                ])

                if stock_moves:
                    # Assuming one move per order line; adjust if multiple moves per line are possible
                    move = stock_moves[0]
                    location = move.location_id  # Source location

                    logger.info(f"Found stock move for line {line.id}: Location '{location.name}'")

                    # Fetch the stock.quant in the specific location
                    location_quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', location.id)
                    ], limit=1)

                    if location_quant:
                        location_name = location_quant.location_id.name
                        location_system = location_quant.location_id.system_type
                        available_qty = location_quant.quantity  # Available quantity in the specific location
                        logger.info(f"Product '{product.name}' available in '{location_name}': {available_qty}")
                    else:
                        location_name = "Unknown"
                        location_system = "Unknown"
                        available_qty = 0
                        logger.warning(f"No stock quant found for product '{product.name}' in location '{location.name}'")
                else:
                    logger.warning(f"No stock move found for order line {line.id} in order {order.name}")
                    location_name = "Unknown"
                    location_system = "Unknown"

                logger.info('----------------------------------------------------------------------------------------------------')
                logger.info(f"Checking product {product.name} (Default Code: {product_default_code}): Ordered {product_qty}, Available {available_qty}")

                if product_qty > available_qty:
                    all_products_available = False
                    logger.warning(f"Insufficient stock for product '{product.name}' in order {order.name}. Required: {product_qty}, Available: {available_qty}")
                    break  # Exit early since one product is insufficient

                # Collect pickings that include the product
                product_pickings = pick_only_picking_records.filtered(
                    lambda p: product.id in p.move_ids.mapped('product_id').ids
                ).mapped('name')

                if not product_pickings:
                    logger.warning(f"No picklist found for product {product.name} in order {order.name}.")
                    product_pickings = ["No picklist"]  # Fallback value
                elif len(product_pickings) > 1:
                    logger.warning(
                        f"Multiple picklists found for product {product.name} in order {order.name}. Using the first one.")
                    product_pickings = product_pickings[:1]  # Take only the first picklist

                # Collect data to be sent to the external system
                products_data.append({
                    'default_code': product_default_code,
                    'product_name': product.name,
                    'quantity': product_qty,
                    'location': location_name,
                    'system': location_system,
                    'product_class': product.automation_manual_product,
                    'picklist': product_pickings[0] if product_pickings else "No picklist",
                })
                logger.debug(f"Product data for {product.name}: {products_data[-1]}")

            # Update order status
            logger.info("Proceeding without authentication...")

            # Proceed with the release process
            if all_products_available:
                order.is_released = 'released'
                # Prepare data to send to external system
                data_to_send = {
                    'order_number': order.name,
                    'products': products_data,
                }
                logger.debug(f"Data to be sent for order {order.name}: {data_to_send}")
                # Send data to external API
                release_url = "https://shiperooconnect.automation.shiperoo.com/api/odoo_release"

                headers = {
                    "Content-Type": "application/json"
                }
                try:
                    response = requests.post(release_url, json=data_to_send, headers=headers)
                    if response.status_code == 200:
                        logger.info(f"Order {order.name} data successfully sent to external system.")
                    else:
                        logger.error(f"Failed to send order {order.name} data to external system. Response: {response.text}")
                        order.is_released = 'unreleased'
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request exception occurred while sending order {order.name}: {e}")
                    order.is_released = 'unreleased'
            else:
                order.is_released = 'unreleased'
                logger.info(f"Order {order.name} released: {order.is_released}")

