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

class TiktokGetAttribute(models.TransientModel):
    _name = 'tiktok.get.attribute'
    _description = 'Tiktok Get Attribute'

    shop_id = fields.Many2one('tiktok.shop', 'Shop')
    locale = fields.Selection([
        ('en-GB','en-GB'),
        ('en-US','en-US'),
        ('id-ID','id-ID'),
        ('ms-MY','ms-MY'),
        ('th-TH','th-TH'),
        ('vi-VN','vi-VN'),
        ('zh-CN','zh-CN')
    ], 'Locale', default='id-ID')
    keyword = fields.Char('Keyword')
    category_version = fields.Selection([
        ('v1','V1'),
        ('v2','V2')
    ], 'Category Version', default='v2')

    def action_confirm(self):
        print('TEST OKE MASUK = = = = = = = =')
        company_obj = self.env['res.company']
        category_obj = self.env['tiktok.category']
        attribute_obj = self.env['tiktok.attribute']
        attribute_line_obj = self.env['tiktok.attribute.value']
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
        locale = self.locale
        category_version = self.category_version
        keyword = self.keyword

        headers = {
            'x-tts-access-token': str(access_token), 
            "Content-type": "application/json"
        }
        category_ids = category_obj.search([('tiktok_category_id','!=', False)])
        for categ in category_ids:
            url = domain+f"/product/202309/categories/{categ.tiktok_category_id}/attributes"+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}"
            sign = company_obj.cal_sign(url, key, headers)
            url = domain+f"/product/202309/categories/{categ.tiktok_category_id}/attributes"+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}"

            res = requests.get(url, headers=headers)
            values = res.json()
                
            for attr in values.get('data').get('attributes',[]):
                attribute_id = attribute_obj.create({
                    'name': attr.get('name'),
                    'is_customizable': attr.get('is_customizable'),
                    'is_multiple_selection': attr.get('is_multiple_selection'),
                    'is_requried': attr.get('is_requried'),
                    'attribute_id': attr.get('attribute_id'),
                    'attribute_type': attr.get('attribute_type')
                })

                for val in attr.get('values'):
                    value_id = attribute_line_obj.create({
                        'value_id': val.get('id'),
                        'name': val.get('name'),
                        'attribute_id': attribute_id.id
                    })