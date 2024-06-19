import json
import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from requests.models import PreparedRequest
req = PreparedRequest()

class TiktokHistoryApi(models.Model):
    _name = 'tiktok.history.api'
    _description = 'Tiktok History API'
    _order = 'create_date desc'

    name = fields.Char('Name')
    
    shop_id = fields.Many2one('tiktok.shop', 'Shop')
    
    total_affected = fields.Integer('Total Affected Records')
    total_inserted = fields.Integer('Total Inserted Records')
    total_updated = fields.Integer('Total Updated Records')
    total_skipped = fields.Integer('Total Skipped Records')
    timestamp = fields.Integer('Timestamp')

    affected_list = fields.Text('Affected Records List')
    skipped_list = fields.Text('Skipped Records List')
    additional_info = fields.Text('Additional Info')
    
    running_date = fields.Datetime('Running Date', default=time.strftime('%Y-%m-%d %H:%M:%S'))
    is_order_date = fields.Boolean('Order Date Selected', default=False)
    state = fields.Selection(selection=[('draft', 'Draft'), ('failed', 'Failed'), ('skipped', 'Skipped'), ('partial', 'Partial'), ('success', 'Success')], string='Status')

    def action_view_form(self):
        for history in self:
            return {
                'name': 'History API',
                'type': 'ir.actions.act_window',
                'res_model': 'tiktok.history.api',
                'res_id': history.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }