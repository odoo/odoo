# -*- encoding: utf-8 -*-
import time
from odoo import api, fields, models, tools, _
from datetime import datetime

class TiktokOrder(models.Model):
    _name = 'tiktok.order'
    _description = 'Tiktok Orders'
    _order = 'update_time desc'

    def _date_update(self):
        res = {}
        for order in self:
            if order.update_time:
                order.date_update = datetime.fromtimestamp(order.update_time).strftime('%Y-%m-%d %H:%M:%S')
            else:
                order.date_update = False

    name = fields.Char('Serial Number')
    shop_id = fields.Many2one('tiktok.shop', 'Shop')
    order_status = fields.Char('Status')
    update_time = fields.Integer('Update Time', default=int(time.time()))
    date_update = fields.Datetime(compute='_date_update',string='Update Date')
    is_updated = fields.Boolean('Updated')
    is_job = fields.Boolean('JOB')