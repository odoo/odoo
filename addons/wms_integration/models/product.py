# -*- coding: utf-8 -*-
import json

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare


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
            body.update({'cursor': cursor})
            resp = requests.post(url, json=body,
                                 headers=wms_attrs.get('headers'))
            print(f'get products offset {resp.status_code}')
            resp_json = resp.json()
            products_wms = resp_json.get('products')
            products += products_wms
            cursor = resp_json.get('cursor')
            if not products:
                break
            if not cursor:
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