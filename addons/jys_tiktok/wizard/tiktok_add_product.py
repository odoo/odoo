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

class TiktokAddProduct(models.TransientModel):
	_name = 'tiktok.add.product'
	_description = 'JYS Tiktok Add Product'

	name = fields.Char('Name')
	shop_id = fields.Many2one('tiktok.shop','Shop')

	def add_product(self):
		print('TEST OKE MASUK = = = = = = = =')
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
		locale = 'id-ID'
		category_version = 'v2'
		path = "/product/202309/categories"

		headers = {
			'x-tts-access-token': str(access_token), 
			"Content-type": "application/json"
		}

		url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}"
		sign = company_obj.cal_sign(ur, key, headers)
		url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}&locale={locale}&category_version={category_version}"

		res = requests.get(url, headers=headers)
		values = res.json()

		print(values,'VALUES===')