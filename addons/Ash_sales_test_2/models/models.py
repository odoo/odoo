from odoo import models, fields, api
import requests
import logging

# from shiperooConnect.interfaces.JB_files.JBxmlrpc_postReceiptstoodoo import picking_id

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
                available_qty = product.qty_available

                # Fetch the stock location using the stock.quant model
                location_quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                
                if location_quant:
                    location_name = location_quant.location_id.name
                    location_system = location_quant.location_id.system_type
                else:
                    location_name = "Unknown"
                    location_system = "Unknown"

                logger.info('----------------------------------------------------------------------------------------------------')
                logger.info(f"Checking product {product.name} (Default Code: {product_default_code}): Ordered {product_qty}, Available {available_qty}")
                if product_qty > available_qty:
                    all_products_available = False
                    break

                # Collect pickings that include the product
                product_pickings = pick_only_picking_records.filtered(
                    lambda p: product.id in p.move_ids.mapped('product_id').ids
                ).mapped('name')

                # Collect data to be sent to the external system
                products_data.append({
                    'default_code': product_default_code,
                    'product_name': product.name,
                    'quantity': product_qty,
                    'location': location_name,
                    'system': location_system,
                    'product_class': product.automation_manual_product,
                    'picklist': product_pickings,
                })

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
                # Send data to external API
                release_url = "https://shiperooconnect.automation.shiperoo.com/api/odoo_release"

                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(release_url, json=data_to_send, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Order {order.name} data successfully sent to external system.")
                else:
                    logger.error(f"Failed to send order {order.name} data to external system. Response: {response.text}")
                    order.is_released = 'unreleased'
            else:
                order.is_released = 'unreleased'
            logger.info(f"Order {order.name} released: {order.is_released}")
