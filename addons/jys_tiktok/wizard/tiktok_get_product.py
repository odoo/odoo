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

class TiktokGetProduct(models.TransientModel):
    _name = 'tiktok.get.product'
    _description = 'Tiktok Get Products'

    shop_id = fields.Many2one('tiktok.shop', 'Shop')

    def action_confirm(self):
        print('OKEEEEEE = = = = =')