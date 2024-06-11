from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokAddProduct(models.TransientModel):
	_name = 'tiktok.add.product'
	_description = 'JYS Tiktok Add Product'

	name = fields.Char('Name')

	def add_product(self):
		print('TEST OKE MASUK = = = = = = = =')

