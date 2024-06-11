import ast
import json
import time
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class TiktokGetOrder(models.TransientModel):
    _name = 'tiktok.get.order'
    _description = 'Tiktok Get Orders'

    is_synced = fields.Boolean('Synced', default=False)
    is_continue = fields.Boolean('Continue Last Sync Date', default=False)
    
    start_date = fields.Datetime('Start Date')
    shop_id = fields.Many2one('tiktok.shop', 'Shop')

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        self.is_synced = False
        self.is_continue = False
        self.start_date = False
        log_obj = self.env['tiktok.history.api']
        last_log_id = log_obj.search([('name', '=', 'Get Orders List'), ('shop_id', '=', self.shop_id.id), ('state', 'in', ['partial', 'success'])], limit=1)
        if last_log_id:
            self.is_synced = True
            self.is_continue = True
            self.start_date = False

    def action_confirm(self):
        print('TEST GET ORDER = = =')