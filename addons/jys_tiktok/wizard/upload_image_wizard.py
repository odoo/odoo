import ast
import json
import requests
import time
import hashlib
import hmac
import math
import base64
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class UploadImageWizard(models.TransientModel):
    _name = 'upload.image.wizard'
    _description = 'Upload Image Wizard'

    name = fields.Char('Name')
    shop_id = fields.Many2one('tiktok.shop','Shop')

    def action_confirm(self):
        product_tmpl_obj = self.env['product.template']
        company_obj = self.env['res.company']
        context = self._context
        print(context,'CONTEXT====')
        company = self.env.company
        shop = self.shop_id
        access_token = shop.tiktok_token
        tiktok_id = shop.shop_id
        chiper = str(shop.tiktok_chiper)
        domain = company.tiktok_api_domain
        app = company.tiktok_client_id
        key = company.tiktok_client_secret
        timest = int(time.time())
        path = '/product/202309/images/upload'
        sign = ''

        headers = {
            'x-tts-access-token': str(access_token)
        }

        product_id = product_tmpl_obj.browse(context.get('active_id'))
        if product_id:
            for img in product_id.tiktok_product_image_ids:
                img_type = f"image/{img.name.split('.')[-1]}"
                img_encode = base64.b64decode(img.image)
                files = {
                  'data': (img.name, img_encode, img_type)
                }
                url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}"
                sign = company_obj.cal_sign(url, key, headers)
                url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}"
                res = requests.post(url, headers=headers, files=files)
                values = res.json()

                print(values,'VALUES===')
                if values.get('data'):
                    img.write({'uri': values.get('data').get('uri')})

