import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class ShopeeItem(models.Model):
    _name = 'shopee.item'
    _description = 'Shopee Items'
    _order = 'update_time desc'

    def _date_update(self):
        for order in self:
            if order.update_time:
                order.date_update = datetime.fromtimestamp(order.update_time).strftime('%Y-%m-%d %H:%M:%S')
            else:
                order.date_update = False

    name = fields.Char('SKU')
    status = fields.Char('Status')

    shop_id = fields.Many2one('shopee.shop', 'Shop')
    item_id = fields.Float('Item ID', size=16, digits=(16,0))
    update_time = fields.Integer('Update Time', default=int(time.time()))
    date_update = fields.Datetime(compute='_date_update', string='Update Date')
    
    is_created = fields.Boolean('Created', default=False)
    is_updated = fields.Boolean('Updated', default=False)
    is_variant_updated = fields.Boolean('Variant Updated', default=False)
    is_done = fields.Boolean('Done', default=False)