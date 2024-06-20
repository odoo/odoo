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

class TiktokGetBrand(models.TransientModel):
    _name = 'tiktok.get.brand'
    _description = 'Tiktok Get Brand'

    shop_id = fields.Many2one('tiktok.shop', 'Shop')
    category_id = fields.Many2one('tiktok.category','Category')
    category_version = fields.Selection([
        ('v1','V1'),
        ('v2','V2')], 'Category Version', default='v2')
    is_authorized = fields.Boolean('Authorized')
    brand_name = fields.Char('Brand Name')

    def action_confirm(self):
        print('TEST OKE MASUK = = = = = = = =')
        brand_obj = self.env['tiktok.brand']
        company_obj = self.env['res.company']
        company = self.env.company
        shop = self.shop_id
        access_token = shop.tiktok_token
        tiktok_id = shop.shop_id
        chiper = str(shop.tiktok_chiper)
        domain = company.tiktok_api_domain
        app = company.tiktok_client_id
        key = company.tiktok_client_secret
        timest = int(time.time())
        sign = ''
        path = '/product/202309/brands'
        page_size = 100
        page_token = False

        headers = {
            'x-tts-access-token': str(access_token), 
            "Content-type": "application/json"
        }
        
        while True:
            base_url = f"{domain}{path}?app_key={app}&access_token={access_token}&timestamp={timest}&shop_cipher={chiper}&page_size={page_size}"

            params = []
            if self.category_id:
                params.append(f"category_id={str(self.category_id.tiktok_category_id)}")
            if self.is_authorized:
                params.append(f"is_authorized={self.is_authorized}")
            if self.brand_name:
                params.append(f"brand_name={self.brand_name}")
            if self.category_version:
                params.append(f"category_version={self.category_version}")
            if page_token:
                params.append(f"page_token={page_token}")

            url = f"{base_url}&{'&'.join(params)}"
            sign = company_obj.cal_sign(url, key, headers)
            url = f"{base_url}&sign={sign}&{'&'.join(params)}"

            res = requests.get(url, headers=headers)
            values = res.json()
            for br in values.get('data').get('brands',[]):
                brand_id = brand_obj.search([('name','=',br.get('name'))])
                if brand_id:
                    continue

                brand = brand_obj.create({
                    'name': br.get('name'),
                    'authorized_status': br.get('authorized_status'),
                    'brand_status': br.get('brand_status'),
                    'brand_id': br.get('id'),
                    'is_t1_brand': br.get('is_t1_brand')
                })
                print(brand)

            if values.get('data').get('next_page_token'):
                page_token = values.get('data').get('next_page_token')
            if not values.get('data').get('next_page_token'):
                break