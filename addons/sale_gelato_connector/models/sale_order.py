from odoo import models
import requests
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def send_gelato_order_request(self):
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56'
        }

        orderUrl = "https://order.gelatoapis.com/v4/orders"
        orderJson = json.dumps({
            "orderType": "order",
            "orderReferenceId": self.id,
            "customerReferenceId": self.partner_id.id,
            "currency": self.currency_id.name,
            "items": self.get_gelato_items(),
            "shipmentMethodUid": "cheapest",
            "shippingAddress": self.get_gelato_shipping_address(),
        }
        )

        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56'
        }
        requests.request("POST", orderUrl, data=orderJson, headers=headers)

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
        for sale_order_line in self.order_line:  # maybe here check if line is a gelato line
            gelato_item = {
                "itemReferenceId": sale_order_line.product_id.product_tmpl_id.id,
                "productUid": str(sale_order_line.product_id.product_tmpl_id.gelato_reference),
                "files": [
                    {
                    "type": "default",
                    "url": str(sale_order_line.product_id.product_tmpl_id.photo_url)
                    }
                ],
                "quantity": int(sale_order_line. product_uom_qty)
            }
            gelato_items.append(gelato_item)

        return gelato_items

    def quote(self):

        url = 'https://order.gelatoapis.com/v4/orders:quote'

        orderJson = json.dumps({
            "orderReferenceId": self.id,
            "customerReferenceId": self.partner_id.id,
            "currency": self.currency_id.name,
            "allowMultipleQuotes": 'true',

            "recipient": self.get_gelato_shipping_address(),
            "products": self.get_gelato_items(),
        }
        )

        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56'
        }

        requests.request("POST", url=url, data=orderJson, headers=headers)  # this gets shipping methods and their price
