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

                location_name = "Unknown"
                location_system = "Unknown"
                manual_location_names = []  # To store manual locations if applicable
                manual_locations_fulfilled_qty = 0  # Track total fulfilled quantity from manual locations

                if location_quant:
                    location_name = location_quant.location_id.name
                    location_system = location_quant.location_id.system_type

                logger.info(
                    '----------------------------------------------------------------------------------------------------')
                logger.info(
                    f"Checking product {product.name} (Default Code: {product_default_code}): Ordered {product_qty}, Available {available_qty}")

                # Check quantity in source location
                product_available_in_source = False
                for picking in pick_only_picking_records:
                    source_location = picking.location_id
                    source_quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', source_location.id)
                    ], limit=1)

                    # If product is manual, check child locations if not available in the source location
                    if not source_quant or source_quant.quantity < product_qty:
                        if product.automation_manual_product == 'manual':
                            child_locations = self.env['stock.location'].search([
                                ('id', 'child_of', source_location.id),
                                ('usage', '=', 'internal')
                            ], order="id asc")  # Sort to prioritize child of child locations

                            for child_location in child_locations:
                                if manual_locations_fulfilled_qty >= product_qty:
                                    break

                                child_quant = self.env['stock.quant'].search([
                                    ('product_id', '=', product.id),
                                    ('location_id', '=', child_location.id)
                                ], limit=1)

                                if child_quant and child_quant.quantity > 0:
                                    fulfilled_qty = min(
                                        product_qty - manual_locations_fulfilled_qty, child_quant.quantity)
                                    manual_locations_fulfilled_qty += fulfilled_qty
                                    manual_location_names.append(
                                        f"{child_location.name} (Fulfilled: {fulfilled_qty})")

                            if manual_locations_fulfilled_qty >= product_qty:
                                product_available_in_source = True
                                break
                    elif source_quant.quantity >= product_qty:
                        product_available_in_source = True
                        break

                # if not product_available_in_source:
                #     logger.warning(
                #         f"Insufficient quantity for product {product.name} in source or child locations for order {order.name}.")
                #     all_products_available = False
                #     break

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
                    # 'location': f"{location_name} (Automation)" if not manual_location_names else
                    #             f"{location_name} (Manual), {', '.join(manual_location_names)} (Manual)",
                    'location': 'Automation',
                    'system': location_system,
                    'product_class': product.automation_manual_product,
                    'picklist': product_pickings[0] if product_pickings else "No picklist",
                })
                logger.debug(f"Product data for {product.name}: {products_data[-1]}")

            # Proceed with the release process
            if all_products_available:
                order.is_released = 'released'
                # Prepare data to send to external system
                data_to_send = {
                    'order_number': order.name,
                    'products': products_data,
                    'tenant_code':order.tenant_code_id.name,
                    'shipping_address' : f"{order.partner_id.name},{order.partner_id.street or ''}",
                }
                logger.info(f"Generated data to release: {data_to_send}")
                logger.debug(f"Data to be sent for order {order.name}: {data_to_send}")
                is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
                # Send data to external API based on env
                release_url = (
                    "https://shiperooconnect-prod.automation.shiperoo.com/api/odoo_release"
                    if is_production == 'True'
                    else "https://shiperooconnect.automation.shiperoo.com/api/odoo_release"
                )
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(release_url, json=data_to_send, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Order {order.name} data successfully sent to external system.")
                else:
                    logger.error(
                        f"Failed to send order {order.name} data to external system. Response: {response.text}")
                    order.is_released = 'unreleased'
            else:
                order.is_released = 'unreleased'
            logger.info(f"Order {order.name} released: {order.is_released}")
