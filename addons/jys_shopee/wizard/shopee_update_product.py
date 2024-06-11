from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ShopeeAddProduct(models.TransientModel):
	_name = 'shopee.update.product'
	_description = 'JYS Shopee Update Product'

	name = fields.Char('Name')
	is_update_price = fields.Boolean('Update Prices')
	is_update_stock = fields.Boolean('Update Stocks')
	is_update_image = fields.Boolean('Update Images')

	def update_product(self):
		print('TEST OKE MASUK = = = = = = = =')
