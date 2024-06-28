import json
import requests

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def send_gelato_order_request(self):
        api_key = self.company_id.gelato_api_key
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        }

        order_url = "https://order.gelatoapis.com/v4/orders"
        order_json = json.dumps({
            "orderType": "order",
            "orderReferenceId": self.id,
            "customerReferenceId": self.partner_id.id,
            "currency": self.currency_id.name,
            "items": self.get_gelato_items(),
            "shipmentMethodUid": "cheapest",
            "shippingAddress": self.get_gelato_shipping_address(),
        }
        )

        requests.request("POST", order_url, data=order_json, headers=headers)

    def action_confirm(self):
        super().action_confirm()
        for sale_order in self:  # maybe here do a check if any product has gelato reference
            sale_order.send_gelato_order_request()

    def get_gelato_shipping_address(self):
        return {  # what if it is created from SO lvl and there is no sufficient information
                "companyName": self.partner_shipping_id.commercial_company_name or '',
                "firstName": self.partner_shipping_id.name,  # required
                "lastName": self.partner_shipping_id.name,  # required
                "addressLine1": self.partner_shipping_id.street,  # this one is required
                "addressLine2": self.partner_shipping_id.street2 or '',
                "state": self.partner_shipping_id.state_id.code,
                "city": self.partner_shipping_id.city,  # this one is required
                "postCode": self.partner_shipping_id.zip,  # this one is required
                "country": self.partner_shipping_id.country_id.code,  # this one is required
                "email": self.partner_shipping_id.email,
                "phone": self.partner_shipping_id.phone or ''
        }

    def get_gelato_items(self):

        gelato_items = []
        gelato_lines = self.order_line.filtered(lambda s: s.product_id.gelato_reference)
        for sale_order_line in gelato_lines:  # maybe here check if line is a gelato line
            gelato_item = {
                "itemReferenceId": sale_order_line.product_id.id,
                "productUid": str(sale_order_line.product_id.gelato_reference),
                "files": [
                    {
                    "type": "default",
                    "url": str(sale_order_line.product_id.product_tmpl_id.gelato_photo_url)
                    }
                ],
                "quantity": int(sale_order_line.product_uom_qty)
            }
            gelato_items.append(gelato_item)

        return gelato_items

    def gelato_cancel(self):
        self.with_context({'disable_cancel_warning': True}).action_cancel()