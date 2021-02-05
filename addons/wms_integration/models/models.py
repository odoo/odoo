# -*- coding: utf-8 -*-
import json

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare


class WMS(models.Model):
    _name = "wms.extension"
    _description = "wms extetension methods"

    def get_wms_attrs(self):
        base_url = self.env['ir.config_parameter'].search(
            [('key', '=', 'wms_url')]).value
        token = self.env['ir.config_parameter'].search(
            [('key', '=', 'wms_api_key')]).value
        wms_order_cursor = self.env['ir.config_parameter'].search(
            [('key', '=', 'wms_order_cursor')]).value
        headers = {
            'Authorization': f'Bearer {token}',
            'content-type': 'application/json'}

        return {
            'base_url': base_url,
            'headers': headers,
            'wms_order_cursor': wms_order_cursor
        }

    def update_order_cursor(self, cursor):
        cursor_line = self.env['ir.config_parameter'].search(
            [('key', '=', 'wms_order_cursor')])
        cursor_line.write({'value': cursor})
        self.env.cr.commit()
        return True

    def send_cancel_acceptance_by_pickings(self, pickings):
        for p in pickings:
            if p.state == 'cancel' and p.picking_type_code not in ('outgoing'):
                wms_warehouse_id = p.move_lines[
                    0].warehouse_id.wms_warehouse_id
                wms = self.env['wms.extension'].get_wms_attrs()
                body = {
                    "status": "cancel",
                    "store_id": f"{wms_warehouse_id}",
                    "external_id": f"{p.id}"
                }
                path = '/api/integration/orders/status'
                url = wms.get('base_url') + path
                responce = requests.post(
                    url,
                    json=body,
                    headers=wms.get('headers')
                )
                answer = responce.json()
                code = answer.get('code')
                if code != 'OK':
                    raise ValidationError(
                        _(f"WMS Can\'t to cancel picking\n"
                          f"{code}"))


class Warehouse(models.Model):
    _inherit = "stock.warehouse"
    _description = "WMS Extension"

    wms_warehouse_id = fields.Char('wms_warehouse_id', index=True,
                                   required=False)


class ProductWMS(models.Model):
    _inherit = 'product.template'
    _description = 'wms_integrations'

    wms_product_id = fields.Char('wms_product_id', index=True, required=False,
                                 translate=False)

    def wms_get_products(self):
        products = []
        wms_attrs = self.env['wms.extension'].get_wms_attrs()
        path = '/api/external/products/v1/products'
        body = {
            "cursor": "",
            "subscribe": False
        }
        url = f"{wms_attrs.get('base_url')}{path}"
        cursor = None
        iteraror = 220
        i = 0
        while True:
            i += 1
            body.update({'cursor': cursor})
            resp = requests.post(url, json=body,
                                 headers=wms_attrs.get('headers'))
            resp_json = resp.json()
            products_wms = resp_json.get('products')
            products += products_wms
            cursor = resp_json.get('cursor')
            if not products:
                break
            if not cursor:
                break
            if i > iteraror:
                break
        return products

    def sync_products(self, wms_products):
        wms_ids = [i.get('product_id') for i in wms_products]
        wms_products = {i.get('product_id'): i for i in wms_products}
        # products = conn.get_model('product.template')
        products_odo = self.search_read(
            [
                ('wms_product_id', 'in', wms_ids)
            ],
            [
                'wms_product_id'
            ]
        )
        products_ids = [i.get('wms_product_id') for i in products_odo]
        for wms_id in wms_ids:
            if wms_id not in products_ids:
                product = wms_products.get(wms_id)
                vals = {
                    'name': product.get('title', ''),
                    'default_code': product.get('external_id'),
                    'wms_product_id': wms_id,
                    'type': 'product',
                    'description': product.get('description')
                }
                self.create(vals)
                print(f'product: {wms_id} prepere to sync')
        self.env.cr.commit()
        print('products commited')
        return True

    def _get_products_from_wms(self):
        wms_products = self.wms_get_products()
        finish = len(wms_products)
        offset = 0
        limit = 20
        while True:
            if limit >= finish:
                limit = finish
            if offset >= finish:
                break
            to_sync = wms_products[offset:limit]
            self.sync_products(to_sync)
            offset = limit
            limit += 20




