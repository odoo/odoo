import ast
import json
import requests
import time
import hashlib
import hmac
import math
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class TiktokGetLogistic(models.TransientModel):
    _name = 'tiktok.get.logistic'
    _description = 'Tiktok Get Logistic'

    shop_id = fields.Many2one('tiktok.shop', 'Shop')

    def action_confirm(self):
        print('TEST OKE MASUK = = = = = = = =')
        logistic_obj = self.env['delivery.carrier']
        company_obj = self.env['res.company']
        company = self.env.company
        shop = self.shop_id
        access_token = shop.tiktok_token
        chiper = str(shop.tiktok_chiper)
        domain = company.tiktok_api_domain
        app = company.tiktok_client_id
        key = company.tiktok_client_secret
        timest = int(time.time())
        sign = ''
        headers = {
            'x-tts-access-token': str(access_token), 
            "Content-type": "application/json"
        }
        
        base_url = f"{domain}/logistics/202309/warehouses?app_key={app}&access_token={access_token}&timestamp={timest}&shop_cipher={chiper}"
        url = f"{base_url}"
        sign = company_obj.cal_sign(url, key, headers)
        url = f"{base_url}&sign={sign}"
        res = requests.get(url, headers=headers)
        values = res.json()
        
        for wh in values.get('data').get('warehouses') : 
            warehouse_id = wh.get('id')
            base_url = f"{domain}/logistics/202309/warehouses/{warehouse_id}/delivery_options?app_key={app}&access_token={access_token}&timestamp={timest}&shop_cipher={chiper}"
            url = f"{base_url}"
            sign = company_obj.cal_sign(url, key, headers)
            url = f"{base_url}&sign={sign}"
            res = requests.get(url, headers=headers)
            values = res.json()
                
            for sp in values.get('data').get('delivery_options') :
                delivery_option_id = sp.get('id')
                base_url = f"{domain}/logistics/202309/delivery_options/{delivery_option_id}/shipping_providers?app_key={app}&access_token={access_token}&timestamp={timest}&shop_cipher={chiper}"
                url = f"{base_url}"
                sign = company_obj.cal_sign(url, key, headers)
                url = f"{base_url}&sign={sign}"
                res = requests.get(url, headers=headers)
                values = res.json()
                
                for ct in values.get('data').get('shipping_providers') :
                    logistic_id = logistic_obj.search([('tiktok_logistic_id','=', ct.get('id'))])
                    if logistic_id:
                        continue
                    logistic_obj.create({
                        'name': ct.get('name'),
                        'tiktok_logistic_id' : ct.get('id'),
                        'product_id' : company.tiktok_logistic_product_id.id
                    })

                    