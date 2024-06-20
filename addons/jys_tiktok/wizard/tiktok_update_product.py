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
	_name = 'tiktok.update.product'
	_description = 'JYS Tiktok Update Product'

	name = fields.Char('Name')
	shop_id = fields.Many2one('tiktok.shop','Shop')
	shop_ids = fields.Many2many('tiktok.shop', 'update_tiktok_id', 'shop_id', 'tiktok_update_product_rel', string='Shops')
	is_update_price = fields.Boolean('Update Prices')
	is_update_stock = fields.Boolean('Update Stocks')
	is_update_image = fields.Boolean('Update Images')

	def update_product(self):
		print('TEST OKE MASUK = = = = = = = =')
		company = self.env.company
		domain = company.tiktok_api_domain
		app = company.tiktok_client_id
		key = company.tiktok_client_secret
		timest = int(time.time())

		for shop in self.shop_ids:
			access_token = shop.tiktok_token
			tiktok_id = shop.shop_id
			chiper = str(shop.tiktok_chiper)
			sign = ''

			for product in self:
				print(product)


