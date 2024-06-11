from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ShopeeAddProduct(models.TransientModel):
	_name = 'shopee.add.product'
	_description = 'JYS Shopee Add Product'

	name = fields.Char('Name')

	def add_product(self):
		print('TEST OKE MASUK = = = = = = = =')

