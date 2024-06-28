# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from odoo import models, fields, _

from odoo.addons.sale_gelato_connector.const import COUNTRIES_WITHOUT_POSTCODES


class ProviderGelato(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('gelato', "Gelato")
    ], ondelete={'gelato': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    def gelato_rate_shipment(self, order):
        url = 'https://order.gelatoapis.com/v4/orders:quote'

        order_json = json.dumps({
            "orderReferenceId": order.id,
            "customerReferenceId": order.partner_id.id,
            "currency": order.currency_id.name,
            "allowMultipleQuotes": 'true',
            "recipient": order.get_gelato_shipping_address(),
            "products": order.get_gelato_items(),
        })

        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': 'db055505-93f4-452e-9084-c2b821391010-76bf5a2e-0f03-4079-87c0-0bf46a7dfedb:eb8d6639-126c-44af-8452-157dc3497196'
        }

        check_value = self.check_required_value(order.partner_id)
        if check_value:
            return {'success': False,
                    'price': 0.0,
                    'error_message': check_value,
                    'warning_message': False}

        request = requests.request("POST", url=url, data=order_json, headers=headers)

        data = json.loads(request.text)
        if data.get('code'):
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error:\n%s', data['message']),
                    'warning_message': False}

        delivery_price = 0
        for i in data['quotes']:
            product_delivery_price = 0

            for y in i['shipmentMethods']:
                if product_delivery_price == 0:
                    product_delivery_price = y['price']
                else:
                    min(product_delivery_price, y['price'])
            delivery_price += product_delivery_price

        return {'success': True,
                'price': delivery_price,
                'error_message': False,
                'warning_message': False
                }

    def check_required_value(self, recipient):

        recipient_required_fields = ['city', 'country_id', 'street']
        if recipient.country_id.code not in COUNTRIES_WITHOUT_POSTCODES:
            recipient_required_fields.append('zip')
        res = [field for field in recipient_required_fields if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)",
                     ", ".join(res).replace("_id", ""))
