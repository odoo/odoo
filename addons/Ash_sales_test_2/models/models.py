from odoo import models, fields, api
import requests
import logging
from odoo.exceptions import UserError, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_released = fields.Selection([
        ('unpicked', 'Unpicked'),
        ('released', 'Released'),
        ('unreleased', 'Unreleased')
    ], string="Is Released", default='unreleased')

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
            products_data = []
            all_products_available = True

            # Get relevant picking records (exclude canceled)
            picking_records = self.env['stock.picking'].search([
                ('origin', '=', order.name),
                ('state', '!=', 'cancel')
            ])
            pick_only_picking_records = picking_records.filtered(
                lambda p: 'Pick' in p.picking_type_id.name
            )

            # Prevent release if any picking is in 'confirmed' (waiting) state
            waiting_pickings = pick_only_picking_records.filtered(lambda p: p.state == 'confirmed')
            if waiting_pickings:
                pick_names = ', '.join(waiting_pickings.mapped('name'))
                raise ValidationError(
                    f"Cannot release order {order.name}: Picking(s) {pick_names} are in 'waiting' state."
                )

            # Prevent release if any picking line is not assigned (fully reserved)
            not_fully_assigned_moves = pick_only_picking_records.mapped('move_ids_without_package').filtered(
                lambda move: move.state != 'assigned'
            )
            if not_fully_assigned_moves:
                move_msgs = []
                for move in not_fully_assigned_moves:
                    reserved = getattr(move, 'quantity_reserved', move.quantity)
                    move_msgs.append(
                        f"{move.product_id.display_name} in picking {move.picking_id.name} "
                        f"(State: {move.state}, Reserved: {reserved}, Needed: {move.product_uom_qty})"
                    )
                raise ValidationError(
                    "Cannot release order %s: The following picking lines are not fully assigned/reserved:\n%s" %
                    (order.name, '\n'.join(move_msgs))
                )

            for line in order.order_line:
                product_qty = line.product_uom_qty
                product = line.product_id
                product_default_code = product.default_code

                location_name = "Unknown"
                manual_location_names = []
                location_system = "Unknown"

                found_in_all_required_picks = True

                # For each picking, check if product is available
                relevant_picks = pick_only_picking_records
                if getattr(order, 'discrete_pick', False):
                    # For discrete pick, only check pickings where this product is present
                    relevant_picks = pick_only_picking_records.filtered(
                        lambda p: product in p.move_ids.mapped('product_id')
                    )

                manual_locations_fulfilled_qty = 0  # Track manual child fulfillment per product

                for picking in relevant_picks:
                    required_qty = product_qty
                    source_location = picking.location_id

                    # Get base location and system (set once)
                    if location_name == "Unknown":
                        location_name = source_location.name
                        location_system = getattr(source_location, 'system_type', "Unknown")

                    # Check in source location
                    source_quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', source_location.id)
                    ], limit=1)
                    fulfilled_qty = source_quant.quantity if source_quant else 0

                    # If manual and not enough, check child locations
                    if fulfilled_qty < required_qty and getattr(product, 'automation_manual_product', '') == 'manual':
                        child_locations = self.env['stock.location'].search([
                            ('id', 'child_of', source_location.id),
                            ('usage', '=', 'internal')
                        ], order="id asc")
                        for child_location in child_locations:
                            if manual_locations_fulfilled_qty >= required_qty:
                                break
                            child_quant = self.env['stock.quant'].search([
                                ('product_id', '=', product.id),
                                ('location_id', '=', child_location.id)
                            ], limit=1)
                            if child_quant and child_quant.quantity > 0:
                                add_qty = min(required_qty - manual_locations_fulfilled_qty, child_quant.quantity)
                                manual_locations_fulfilled_qty += add_qty
                                manual_location_names.append(f"{child_location.name} (Fulfilled: {add_qty})")

                        fulfilled_qty += manual_locations_fulfilled_qty

                    if fulfilled_qty < required_qty:
                        logger.warning(
                            f"Product {product.name} not available in picking {picking.name} "
                            f"(needed {required_qty}, found {fulfilled_qty})."
                        )
                        found_in_all_required_picks = False
                        break  # Don't need to check other pickings, already failed

                if not found_in_all_required_picks:
                    all_products_available = False
                    raise ValidationError(
                        f"Cannot release order {order.name}: "
                        f"Product '{product.name}' does not have enough stock in all required pickings."
                    )

                # Prepare picklist info (as in your existing logic)
                product_pickings = pick_only_picking_records.filtered(
                    lambda p: product.id in p.move_ids.mapped('product_id').ids
                ).mapped('name')
                if not product_pickings:
                    product_pickings = ["No picklist"]
                elif len(product_pickings) > 1:
                    product_pickings = product_pickings[:1]

                products_data.append({
                    'default_code': product_default_code,
                    'product_name': product.name,
                    'quantity': product_qty,
                    'location': f"{location_name} (Automation)" if not manual_location_names else
                    f"{location_name} (Manual), {', '.join(manual_location_names)} (Manual)",
                    'system': location_system,
                    'product_class': getattr(product, 'automation_manual_product', ''),
                    'picklist': product_pickings[0],
                })
                logger.debug(f"Product data for {product.name}: {products_data[-1]}")

            # --- Proceed if all products available in all picks ---
            if all_products_available:
                order.is_released = 'released'
                data_to_send = {
                    'order_number': order.name,
                    'products': products_data,
                    'tenant_code': order.tenant_code_id.name,
                    'name': order.partner_id.name,
                    'street1': order.partner_id.street,
                    'street2': order.partner_id.street2,
                    'city': order.partner_id.city,
                    'state': order.partner_id.state_id.name if order.partner_id.state_id else '',
                    'country': order.partner_id.country_id.name if order.partner_id.country_id else '',
                    'zip': order.partner_id.zip,
                    'discrete_pick': getattr(order, 'discrete_pick', False),
                }
                logger.info(f"Generated data to release: {data_to_send}")
                is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
                release_url = (
                    "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/odoo_release"
                    if is_production == 'True'
                    else "https://shiperooconnect-dev.automation.shiperoo.com/api/odoo_release"
                )
                headers = {"Content-Type": "application/json"}
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

