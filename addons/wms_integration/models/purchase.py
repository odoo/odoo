# -*- coding: utf-8 -*-
import json

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare



class PurchaseWMS(models.Model):
    _inherit = "purchase.order"
    wms_order_id = fields.Char('wms_order_id', copy=False,
                               help="WMS orderID")
    wms_order_type = fields.Char('wms_order_type', copy=False,
                               help="WMS order_type")

    def order_exist_wms(self, order):
        a=1

    def send_acceptance(self, picking):
        url = self.env['ir.config_parameter'].search(
            [('key', '=', 'wms_url')]).value
        token = self.env['ir.config_parameter'].search(
            [('key', '=', 'wms_api_key')]).value
        url = f'{url}/api/integration/orders/create'
        required = [
            {
                "product_id": i.product_id.wms_product_id,
                "count": int(i.purchase_line_id.product_qty),
                "price": f'{i.purchase_line_id.price_unit}',
                "price_unit": 1
            }
            for i in picking.move_lines
        ]
        doc_date = picking.date.strftime("%Y-%m-%d")
        try:
            warehouse_id = picking.move_lines[0].warehouse_id.wms_warehouse_id
        except Exception as ex:
            raise ValidationError(_(f"WMS ERROR: {ex}"))
        body = {
            "store_id": f"{warehouse_id}",
            "type": "acceptance",
            "approved": True,
            "source": "1c",
            "attr": {
                "doc_date": f"{doc_date}",
                "contractor": self.partner_id.name,
                "request_id": f'{picking.id}',
                "request_number": picking.origin,
                "request_type": picking.move_type,
                "doc_number": picking.name
            },
            "required": required,
            "external_id": f'{picking.id}'
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'content-type': 'application/json'}
        responce = requests.post(url, json=body, headers=headers)
        if responce.status_code != 200:
            raise ValidationError(_(f"WMS Error Acceptance is not created \n"
                                    f"{responce.text}"))
        picking.wms_order_id = json.dumps(
            [responce.json().get('order').get('order_id')])
        picking.wms_order_type = 'acceptance'
        return picking.wms_order_id

