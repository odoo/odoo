from odoo import Command, fields, models, _
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
            "items": [
                {
                    "itemReferenceId": "1",
                    "productUid": "phonecase_apple_iphone-15promax_slim_white_glossy",
                    "files": [
                        {
                            "type": "default",
                            "url": "https://www.dropbox.com/scl/fi/h04dgs73h9sq0hefgjjhh/test3.png?rlkey=m1g2871gd5gfrngo7hmu0jc1b&st=cij8q29w&dl=1"
                        }
                    ],
                    "quantity": 1
                },
                {
                    "itemReferenceId": "2",
                    "productUid": "canvas_200x200-mm-8x8-inch_canvas_wood-fsc-slim_4-0_hor",
                    "files": [
                        {
                            "type": "default",
                            "url": "https://images.rawpixel.com/image_png_800/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDIzLTA5L3Jhd3BpeGVsX29mZmljZV8yOF9mZW1hbGVfbWluaW1hbF9yb2JvdF9mYWNlX29uX2RhcmtfYmFja2dyb3VuZF81ZDM3YjhlNy04MjRkLTQ0NWUtYjZjYy1hZmJkMDI3ZTE1NmYucG5n.png"
                        }
                    ],
                    "quantity": 1
                }
            ],
            "shipmentMethodUid": "fed_ex_2_day",
            "shippingAddress": { #maybe throw it in sepate function
                "companyName": self.partner_shipping_id.company_name or '',
                "firstName": self.partner_shipping_id.name,
                "lastName": self.partner_shipping_id.name,
                "addressLine1": self.partner_shipping_id.street,
                "addressLine2": self.partner_shipping_id.street2,
                "state": self.partner_shipping_id.state_id.code,
                "city": self.partner_shipping_id.city,
                "postCode": self.partner_shipping_id.zip,
                "country": self.partner_shipping_id.country_id.code,
                "email": self.partner_shipping_id.email,
                "phone": self.partner_shipping_id.phone
            }
        }
        )
        headers = {
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56',

        }
        # url = 'https://shipment.gelatoapis.com/v1/shipment-methods?country=' + self.partner_shipping_id.country_code
        # shipping = requests.request("GET", url=url, headers=headers)
        #x = shipping.json()
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56'
        }
        response = requests.request("POST", orderUrl, data=orderJson, headers=headers)
        print(response)

    def action_confirm(self):
        super().action_confirm()
        self.send_gelato_order_request()