from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import time

class ShopeeOrder(models.Model):
	_name = 'shopee.order'
	_description = 'Shopee Order'

	name = fields.Char('No. Pesanan')
	status = fields.Char('Status Pesanan')
	is_updated = fields.Boolean('Updated', default=False)
	update_time = fields.Integer('Update Time', default=int(time.time()))
	date_update = fields.Datetime(compute='_date_update', string='Update Date')
	shop_id = fields.Many2one('shopee.shop', 'Shop')

	def _date_update(self):
		for order in self:
			if order.update_time:
				order.date_update = datetime.fromtimestamp(order.update_time).strftime('%Y-%m-%d %H:%M:%S')
			else:
				order.date_update = False