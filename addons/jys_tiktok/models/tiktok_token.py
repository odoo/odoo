# -*- encoding: utf-8 -*-
import time
import json
import requests
import hashlib
import hmac
from odoo import api, fields, models, tools, _

import requests

class TiktokToken(models.Model):
    _name = 'tiktok.token'
    _order = 'id desc'
    
    name = fields.Char('Name')
    access_token = fields.Char('Access Token')
    valid = fields.Integer('Valid On (Days)')
    expires_in = fields.Datetime('Expire Client Secret')
    
    token_type = fields.Char('Tiktok Client Secret')
        
    
    
    
    
    
            
        
    