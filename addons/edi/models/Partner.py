# -*- coding: utf-8 -*-

from datetime import datetime
import json
from platform import platform
import requests
from odoo import models, fields, api


class Partner(models.Model):
    _name = 'edi.partner'
    _description = 'partners for edi'

    name = fields.Char('Name')
    description = fields.Text('Description')
    inventory_sync = fields.Boolean('Send Inventory?')
    get_orders = fields.Boolean(
        string='Get Orders',
    )
    fulfillment_sync = fields.Boolean('Fulfillment Sync?')
    inventory_locations = fields.Text('Inventory Locations')
    platform = fields.Selection(
        string='Platform',
        selection=[('logicBroker', 'LogicBroker'), ('mirakl', 'Mirakl')]
    )
    api_key = fields.Text(
        string='Api Key',
    )
    
    lookback_date = fields.Datetime(
        string='Lookback Date',
        default=fields.Datetime.now,
    )
    
    last_order_id = fields.Integer(
        string='Last Order Id',
    )
    def get_orders(self):
        orderList = []
        if(self.platform=='logicbroker'):
            page =0
            TotalPages=1
            isoString= datetime.now().isoformat()
            subkey = self.api_key
            pageSize=100
            while page<TotalPages:
                storeUrl = f'https://commerceapi.io/api/v2/Orders?subscription-key=${subkey}&Filters.status=150&Filters.from=${isoString}&Filters.page=${page}&Filters.pageSize={pageSize}'
                print(f'url:{storeUrl}')
                resp = requests.get(storeUrl)
                print(resp.text)
                resp_data= json.loads(resp.text)
                orderList+=resp_data.get('Records')
                TotalPages = resp_data.get("TotalPages")
                page+=1
                print(f'got page {page} of {TotalPages}')
        else:
            print(f'unmapped platform {platform}')
        return orderList
    
    

    # add methods, get osi, create so, send shipment, send invoice, send inventory
    