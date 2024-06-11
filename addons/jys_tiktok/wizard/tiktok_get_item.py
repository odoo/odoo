import json
import time
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class TiktokGetItem(models.TransientModel):
    _name = 'tiktok.get.item'
    _description = 'Tiktok Get Items'

    shop_ids = fields.Many2many('tiktok.shop', 'tiktok_item_product_shop_rel', 'item_wizard_id', 'shop_id', string='Shops')
    method = fields.Selection([('-1', 'Create and Update Items'), ('-2', 'Only Update Items')], 'Method', default='-2')
    is_update_variant = fields.Boolean('Update Variants', default=False)
    is_merge_name = fields.Boolean('Merge Same Products by Name', default=True)
    is_merge_sku = fields.Boolean('Merge Same Products by SKU', default=True)

    def action_confirm(self):
        print('TEST GET ITEM = = = = =')