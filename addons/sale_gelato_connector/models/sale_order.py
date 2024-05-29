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
        product = str(self.order_line[0].product_id.gelato_reference) or 'phonecase_apple_iphone-15promax_slim_white_glossy'
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
                    "productUid": product,
                    "files": [
                        {
                            "type": "default",
                            "url": "https://www.dropbox.com/scl/fi/4st0vrjx7dwdvckmtcuaj/template_for_mug.pdf?rlkey=sqfyy3ftllcnlb5n4qhy2hdaw&st=82ke4st0&dl=1"
                        }
                    ],
                    "quantity": 1
                },
                {
                    "itemReferenceId": "3",
                    "productUid": "framed_poster_mounted_premium_130x180-mm-5x7-inch_black_wood_w20xt20-mm_plexiglass_130x180-mm-5r_200-gsm-80lb-uncoated_4-0_hor",
                    "files": [
                        {
                            "type": "default",
                            "url": "https://www.dropbox.com/scl/fi/efuorqtarlq7gvtn7raq5/gelato.framed_poster_mounted_premium_130x180-mm-5x7-inch_black_wood_w20xt20-mm_plexiglass_130x180-mm-5r_250-gsm-100lb-uncoated-offwhite-archival_4-0_hor.pdf?rlkey=j9d85neowcz5adna0rxlf4l9u&st=70vakxif&dl=1"
                        }
                    ],
                    "quantity": 1
                }
            ],
            "shipmentMethodUid": "fed_ex_2_day",
            "shippingAddress": self.get_gelato_shipping_address(),
        }
        )
        headers = {
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56',

        }
        # url = 'https://shipment.gelatoapis.com/v1/shipment-methods?country=' + self.partner_shipping_id.country_code
        # shipping = requests.request("GET", url=url, headers=headers)
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': 'dada2370-fb2d-4800-8a3a-80fbdf331ef9-826e7758-6a44-4bf6-9dbd-d7d1daabc250:c5524bcc-2dff-4efb-aeb3-03a8b08a0e56'
        }
        response = requests.request("POST", orderUrl, data=orderJson, headers=headers)
        print(response)

    def action_confirm(self):
        super().action_confirm()
        for sale_order in self:
            sale_order.send_gelato_order_request()

    def get_gelato_shipping_address(self):
        return {
                "companyName": self.partner_shipping_id.commercial_company_name or '',
                "firstName": self.partner_shipping_id.name, #required
                #"lastName": self.partner_shipping_id.name, #required
                "addressLine1": self.partner_shipping_id.street, #this one is required
                "addressLine2": self.partner_shipping_id.street2 or '',
                "state": self.partner_shipping_id.state_id.code,
                "city": self.partner_shipping_id.city, #this one is required
                "postCode": self.partner_shipping_id.zip, #this one is required
                "country": self.partner_shipping_id.country_id.code, #this one is required
                "email": self.partner_shipping_id.email,
                "phone": self.partner_shipping_id.phone or ''
        }
