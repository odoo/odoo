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

class TiktokGetCategory(models.TransientModel):
    _name = 'tiktok.get.category'
    _description = 'Tiktok Get Category'

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
        company_obj = self.env['res.company']
        category_obj = self.env['tiktok.category']
        category_rule_obj = self.env['tiktok.category.rules']
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
        path = "/product/202309/categories"

        headers = {
            'x-tts-access-token': str(access_token), 
            "Content-type": "application/json"
        }
        if not keyword:
            url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}"
            sign = company_obj.cal_sign(url, key, headers)
            url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}"
        if keyword:
            url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}&keyword={keyword}"
            sign = company_obj.cal_sign(url, key, headers)
            url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}&keyword={keyword}"

        res = requests.get(url, headers=headers)
        values = res.json()

        for cat in values.get('data').get('categories'):
            category_id = cat.get('id')
            categ_id = category_obj.search([('tiktok_category_id','=', int(category_id))], limit=1)
            if categ_id:
                continue 
            values = {
                'name': cat.get('local_name'),
                'is_leaf': cat.get('is_leaf'),
                'tiktok_category_id': int(category_id),
                'tiktok_parent_id': int(cat.get('parent_id')),
                'permission_statuses': str(cat.get('permission_statuses'))
            }
            cat_id = category_obj.create(values)
            url = domain+f"/product/202309/categories/{category_id}/rules"+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&category_version={category_version}"
            sign = company_obj.cal_sign(url, key, headers)
            url = domain+f"/product/202309/categories/{category_id}/rules"+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&category_version={category_version}"
            res_cat = requests.get(url, headers=headers)
            values_cat = res_cat.json()
            data = values_cat.get('data')
            rules_ids = {}
            if data:
                rules_ids = {
                    'name': data.get('product_certifications')[0].get('name') if len(data.get('product_certifications')) > 0 else False,
                    'cod': data.get('cod').get('is_supported'),
                    'epr': data.get('epr').get('is_required'),
                    'package_dimension': data.get('package_dimension').get('is_required'),
                    'size_sup': data.get('size_chart').get('is_supported'),
                    'size_req': data.get('size_chart').get('is_required'),
                    'certif_id': data.get('product_certifications')[0].get('id') if len(data.get('product_certifications')) > 0 else False,
                    'certif_req': data.get('product_certifications')[0].get('is_required') if len(data.get('product_certifications')) > 0 else False,
                    'url': data.get('product_certifications')[0].get('sample_image_url') if len(data.get('product_certifications')) > 0 else False,
                    'tiktok_category_id': cat_id.id
                }

            if rules_ids:
                category_rule_obj.create(rules_ids)
