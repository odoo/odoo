import time
import json
import requests
import hashlib
import hmac
import PyPDF2 # type: ignore
import io
import base64
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse # type: ignore

class TiktokBrand(models.Model):
    _name = 'tiktok.brand'
    _description = 'Tiktok Brand'

    name = fields.Char('Name')   

    authorized_status = fields.Char('Auth Status')
    brand_id = fields.Char('Brand ID')
    is_t1_brand = fields.Boolean('T1 Brand')
    brand_status = fields.Char('Brand Status')
    
    def create_brand(self):
        context = self.env.context
        company = self.env.company 
        domain = company.tiktok_api_domain
        company_obj = self.env['res.company']
        app = company.tiktok_client_id
        domain = company.tiktok_api_domain
        key = company.tiktok_client_secret
        sign = ''
        shops = self.env['tiktok.shop'].search([])
        
        for shop in shops :
            access_token = shop.tiktok_token
            headers = {
                'x-tts-access-token': str(access_token), 
                "Content-type": "application/json"
            }
            timest = int(time.time())
            for brand in self.browse(context.get('active_ids')) :
                params = {'name' : brand.name}
                url =  domain+"/product/202309/brands?app_key=%s&sign=%s&timestamp=%s"%(app,sign,timest)
                sign = company_obj.cal_sign(url, key, headers, params)
                url =  domain+"/product/202309/brands?app_key=%s&sign=%s&timestamp=%s"%(app,sign,timest)
                print(url)
                res = requests.post(url, headers=headers , json=params)
                values = res.json()
                print(values)