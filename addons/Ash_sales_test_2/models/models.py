from odoo import models, fields, api
import requests

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_released = fields.Selection([
        ('unpicked', 'Unpicked'),
        ('released', 'Released'),
        ('unreleased', 'Unreleased')
    ], string="Is Released", default='unpicked')

    customer_name = fields.Char(string="Name", required=True)
    customer_address = fields.Char(string="Address", required=True)
    customer_suburb = fields.Char(string="Suburb", required=True)
    customer_state = fields.Char(string="State", required=True)
    customer_postcode = fields.Char(string="Postcode", required=True)
    customer_email = fields.Char(string="Email Address")
    customer_phone = fields.Char(string="Phone Number")

    def action_release_quotations(self):
        print(f"action_release_quotations called with {len(self)} orders")
        if not self:
            print("No orders passed to action_release_quotations")
        for order in self:
            print(f"Processing order: {order.name}")
            all_products_available = True
            products_data = []
            for line in order.order_line:
                product_qty = line.product_uom_qty  
                available_qty = line.product_id.qty_available

                # Fetch the stock location using the stock.quant model
                location_quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                
                if location_quant:
                    location_name = location_quant.location_id.name
                    location_system = location_quant.location_id.system_type
                else:
                    location_name = "Unknown"
                    location_system = "Unknown"

                print('----------------------------------------------------------------------------------------------------')
                print(f"Checking product {line.product_id.name}: Ordered {product_qty}, Available {available_qty}")
                if product_qty > available_qty:
                    all_products_available = False
                    break

                # Collect data to be sent to the external system
                products_data.append({
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'quantity': product_qty,
                    'location': location_name,
                    'system': location_system,
                })

            # Update order status
        auth_url = "https://shiperooconnect.automation.shiperoo.com/api/authenticate"
        auth_data = {
            "client_id": "valid_client",
            "client_secret": "valid_secret"
        }
        auth_response = requests.post(auth_url, json=auth_data)

        if auth_response.status_code == 200:
            session_id = auth_response.json().get("session_id")
            print(f"Authenticated successfully. Session ID: {session_id}")

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
                    "shipConnect": session_id,
                    "Content-Type": "application/json"
                }
                response = requests.post(release_url, json=data_to_send, headers=headers)
                if response.status_code == 200:
                    print(f"Order {order.name} data successfully sent to external system.")
                else:
                    print(f"Failed to send order {order.name} data to external system. Response: {response.text}")
                    order.is_released = 'unreleased'
            else:
                order.is_released = 'unreleased'
            print(f"Order {order.name} released: {order.is_released}")

        else:
            print("Failed to authenticate. Cannot proceed with the release process.")